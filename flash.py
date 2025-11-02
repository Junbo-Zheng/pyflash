#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import serial
import serial.tools.list_ports
import threading
import os
import time
from pathlib import Path

class AdvancedSerialFlasher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("高级串口烧录工具")
        self.root.geometry("800x600")
        
        # 存储固件和资源文件
        self.firmware_files = []
        self.resource_files = []
        
        # 串口连接
        self.serial_conn = None
        self.is_flashing = False
        
        self.setup_ui()
        self.refresh_ports()
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 串口设置区域
        serial_frame = ttk.LabelFrame(main_frame, text="串口设置", padding="5")
        serial_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 串口选择
        ttk.Label(serial_frame, text="串口号:").grid(row=0, column=0, sticky=tk.W)
        self.port_combo = ttk.Combobox(serial_frame, width=15, state="readonly")
        self.port_combo.grid(row=0, column=1, padx=5)
        
        # 波特率选择
        ttk.Label(serial_frame, text="波特率:").grid(row=0, column=2, sticky=tk.W, padx=(20,0))
        self.baud_combo = ttk.Combobox(serial_frame, width=10, values=[
            "9600", "19200", "38400", "57600", "115200", "230400", 
            "460800", "921600", "1500000"
        ], state="readonly")
        self.baud_combo.set("115200")
        self.baud_combo.grid(row=0, column=3, padx=5)
        
        # 刷新串口按钮
        self.refresh_btn = ttk.Button(serial_frame, text="刷新串口", command=self.refresh_ports)
        self.refresh_btn.grid(row=0, column=4, padx=10)
        
        # 连接按钮
        self.connect_btn = ttk.Button(serial_frame, text="打开串口", command=self.toggle_serial)
        self.connect_btn.grid(row=0, column=5, padx=5)
        
        # 固件管理区域
        firmware_frame = ttk.LabelFrame(main_frame, text="固件文件", padding="5")
        firmware_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 固件按钮框架
        firmware_btn_frame = ttk.Frame(firmware_frame)
        firmware_btn_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        ttk.Button(firmware_btn_frame, text="添加固件", 
                  command=self.add_firmware).pack(side=tk.LEFT, padx=2)
        ttk.Button(firmware_btn_frame, text="移除选中", 
                  command=self.remove_selected_firmware).pack(side=tk.LEFT, padx=2)
        ttk.Button(firmware_btn_frame, text="清空列表", 
                  command=self.clear_firmware).pack(side=tk.LEFT, padx=2)
        
        # 固件列表
        firmware_list_frame = ttk.Frame(firmware_frame)
        firmware_list_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        columns = ("文件名", "大小", "路径")
        self.firmware_tree = ttk.Treeview(firmware_list_frame, columns=columns, show="headings", height=6)
        
        for col in columns:
            self.firmware_tree.heading(col, text=col)
            self.firmware_tree.column(col, width=100)
        
        self.firmware_tree.column("路径", width=200)
        
        scrollbar = ttk.Scrollbar(firmware_list_frame, orient=tk.VERTICAL, command=self.firmware_tree.yview)
        self.firmware_tree.configure(yscrollcommand=scrollbar.set)
        
        self.firmware_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 资源文件区域
        resource_frame = ttk.LabelFrame(main_frame, text="资源文件", padding="5")
        resource_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 资源按钮框架
        resource_btn_frame = ttk.Frame(resource_frame)
        resource_btn_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        ttk.Button(resource_btn_frame, text="添加资源", 
                  command=self.add_resource).pack(side=tk.LEFT, padx=2)
        ttk.Button(resource_btn_frame, text="移除选中", 
                  command=self.remove_selected_resource).pack(side=tk.LEFT, padx=2)
        ttk.Button(resource_btn_frame, text="清空列表", 
                  command=self.clear_resource).pack(side=tk.LEFT, padx=2)
        
        # 资源列表
        resource_list_frame = ttk.Frame(resource_frame)
        resource_list_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.resource_tree = ttk.Treeview(resource_list_frame, columns=columns, show="headings", height=6)
        
        for col in columns:
            self.resource_tree.heading(col, text=col)
            self.resource_tree.column(col, width=100)
        
        self.resource_tree.column("路径", width=200)
        
        scrollbar_res = ttk.Scrollbar(resource_list_frame, orient=tk.VERTICAL, command=self.resource_tree.yview)
        self.resource_tree.configure(yscrollcommand=scrollbar_res.set)
        
        self.resource_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_res.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 烧录控制区域
        control_frame = ttk.LabelFrame(main_frame, text="烧录控制", padding="5")
        control_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # 烧录选项
        option_frame = ttk.Frame(control_frame)
        option_frame.grid(row=0, column=0, sticky=tk.W)
        
        self.auto_reset_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(option_frame, text="自动复位", 
                       variable=self.auto_reset_var).pack(side=tk.LEFT, padx=5)
        
        self.verify_flash_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(option_frame, text="校验烧录", 
                       variable=self.verify_flash_var).pack(side=tk.LEFT, padx=5)
        
        # 烧录按钮
        self.flash_btn = ttk.Button(control_frame, text="开始烧录", 
                                   command=self.start_flash, state=tk.DISABLED)
        self.flash_btn.grid(row=0, column=1, padx=20)
        
        self.stop_btn = ttk.Button(control_frame, text="停止烧录", 
                                  command=self.stop_flash, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=2, padx=5)
        
        # 进度区域
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(progress_frame, text="进度:").pack(side=tk.LEFT)
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.pack(side=tk.RIGHT)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="烧录日志", padding="5")
        log_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 日志文本框和滚动条
        self.log_text = tk.Text(log_frame, height=12, wrap=tk.WORD)
        scrollbar_log = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar_log.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_log.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 配置权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        firmware_frame.columnconfigure(0, weight=1)
        firmware_frame.rowconfigure(1, weight=1)
        firmware_list_frame.columnconfigure(0, weight=1)
        firmware_list_frame.rowconfigure(0, weight=1)
        resource_frame.columnconfigure(0, weight=1)
        resource_frame.rowconfigure(1, weight=1)
        resource_list_frame.columnconfigure(0, weight=1)
        resource_list_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
    def refresh_ports(self):
        """刷新可用串口列表"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.set(ports[0])
        else:
            self.port_combo.set('')
    
    def toggle_serial(self):
        """打开/关闭串口连接"""
        if self.serial_conn and self.serial_conn.is_open:
            self.close_serial()
        else:
            self.open_serial()
    
    def open_serial(self):
        """打开串口连接"""
        port = self.port_combo.get()
        baudrate = self.baud_combo.get()
        
        if not port:
            messagebox.showerror("错误", "请选择串口")
            return
        
        try:
            self.serial_conn = serial.Serial(
                port=port,
                baudrate=int(baudrate),
                timeout=1
            )
            self.connect_btn.config(text="关闭串口")
            self.flash_btn.config(state=tk.NORMAL)
            self.log("串口已打开: {} @ {}bps".format(port, baudrate))
        except Exception as e:
            messagebox.showerror("错误", "无法打开串口: {}".format(str(e)))
    
    def close_serial(self):
        """关闭串口连接"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.connect_btn.config(text="打开串口")
        self.flash_btn.config(state=tk.DISABLED)
        self.log("串口已关闭")
    
    def add_firmware(self):
        """添加固件文件"""
        files = filedialog.askopenfilenames(
            title="选择固件文件",
            filetypes=[("二进制文件", "*.bin"), ("所有文件", "*.*")]
        )
        for file_path in files:
            self.add_file_to_list(file_path, self.firmware_files, self.firmware_tree, "固件")
    
    def add_resource(self):
        """添加资源文件"""
        files = filedialog.askopenfilenames(
            title="选择资源文件",
            filetypes=[("资源文件", "*.bin *.img *.dat *.cfg"), ("所有文件", "*.*")]
        )
        for file_path in files:
            self.add_file_to_list(file_path, self.resource_files, self.resource_tree, "资源")
    
    def add_file_to_list(self, file_path, file_list, treeview, file_type):
        """添加文件到列表"""
        if file_path and file_path not in [f[0] for f in file_list]:
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            file_list.append((file_path, file_name, file_size))
            
            # 添加到Treeview
            treeview.insert("", tk.END, values=(file_name, self.format_file_size(file_size), file_path))
    
    def remove_selected_firmware(self):
        """移除选中的固件"""
        self.remove_selected_item(self.firmware_tree, self.firmware_files)
    
    def remove_selected_resource(self):
        """移除选中的资源"""
        self.remove_selected_item(self.resource_tree, self.resource_files)
    
    def remove_selected_item(self, treeview, file_list):
        """移除选中的项目"""
        selected = treeview.selection()
        if selected:
            for item in selected:
                values = treeview.item(item)['values']
                if values:
                    file_path = values[2]  # 路径在第三列
                    # 从文件列表中移除
                    file_list[:] = [f for f in file_list if f[0] != file_path]
                treeview.delete(item)
    
    def clear_firmware(self):
        """清空固件列表"""
        self.firmware_files.clear()
        for item in self.firmware_tree.get_children():
            self.firmware_tree.delete(item)
    
    def clear_resource(self):
        """清空资源列表"""
        self.resource_files.clear()
        for item in self.resource_tree.get_children():
            self.resource_tree.delete(item)
    
    def format_file_size(self, size):
        """格式化文件大小显示"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def start_flash(self):
        """开始烧录过程"""
        if not self.serial_conn or not self.serial_conn.is_open:
            messagebox.showerror("错误", "请先打开串口")
            return
        
        if not self.firmware_files and not self.resource_files:
            messagebox.showerror("错误", "请添加要烧录的文件")
            return
        
        self.is_flashing = True
        self.flash_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.connect_btn.config(state=tk.DISABLED)
        
        # 在新线程中执行烧录
        thread = threading.Thread(target=self.flash_process)
        thread.daemon = True
        thread.start()
    
    def stop_flash(self):
        """停止烧录过程"""
        self.is_flashing = False
        self.log("正在停止烧录...")
    
    def flash_process(self):
        """烧录处理主函数"""
        try:
            total_files = len(self.firmware_files) + len(self.resource_files)
            current_file = 0
            
            # 烧录固件文件
            for file_path, file_name, file_size in self.firmware_files:
                if not self.is_flashing:
                    break
                
                current_file += 1
                progress = (current_file - 1) / total_files * 100
                self.update_progress(progress)
                
                self.log(f"开始烧录固件: {file_name}")
                success = self.flash_firmware(file_path, file_name)
                
                if success:
                    self.log(f"固件烧录成功: {file_name}")
                else:
                    self.log(f"固件烧录失败: {file_name}")
                    if not self.is_flashing:
                        break
            
            # 烧录资源文件
            for file_path, file_name, file_size in self.resource_files:
                if not self.is_flashing:
                    break
                
                current_file += 1
                progress = (current_file - 1) / total_files * 100
                self.update_progress(progress)
                
                self.log(f"开始烧录资源: {file_name}")
                success = self.flash_resource(file_path, file_name)
                
                if success:
                    self.log(f"资源烧录成功: {file_name}")
                else:
                    self.log(f"资源烧录失败: {file_name}")
                    if not self.is_flashing:
                        break
            
            if self.is_flashing:
                self.update_progress(100)
                self.log("所有文件烧录完成!")
            else:
                self.log("烧录过程被用户中断")
                
        except Exception as e:
            self.log(f"烧录过程中发生错误: {str(e)}")
        finally:
            self.flash_complete()
    
    def flash_firmware(self, file_path, file_name):
        """烧录固件文件的具体实现"""
        # 这里实现具体的固件烧录逻辑
        # 例如: 发送进入bootloader命令、擦除flash、分块写入数据、校验等
        
        try:
            # 模拟烧录过程
            with open(file_path, 'rb') as f:
                data = f.read()
                file_size = len(data)
                
                # 发送烧录命令
                self.serial_conn.write(b'FLASH_START\n')
                time.sleep(0.1)
                
                # 分块发送数据
                chunk_size = 1024
                for i in range(0, file_size, chunk_size):
                    if not self.is_flashing:
                        return False
                    
                    chunk = data[i:i+chunk_size]
                    self.serial_conn.write(chunk)
                    
                    # 更新进度
                    progress = min(100, (i + len(chunk)) / file_size * 100)
                    self.root.after(0, lambda: self.update_progress(progress))
                    
                    time.sleep(0.01)  # 模拟传输延迟
                
                # 发送结束命令
                self.serial_conn.write(b'FLASH_END\n')
                
            return True
        except Exception as e:
            self.log(f"固件烧录错误: {str(e)}")
            return False
    
    def flash_resource(self, file_path, file_name):
        """烧录资源文件的具体实现"""
        # 这里实现具体的资源烧录逻辑
        # 可能与固件烧录逻辑不同
        
        try:
            # 模拟资源烧录过程
            with open(file_path, 'rb') as f:
                data = f.read()
                file_size = len(data)
                
                # 发送资源烧录命令
                self.serial_conn.write(b'RESOURCE_START\n')
                time.sleep(0.1)
                
                # 分块发送数据
                chunk_size = 512  # 资源文件可能使用不同的块大小
                for i in range(0, file_size, chunk_size):
                    if not self.is_flashing:
                        return False
                    
                    chunk = data[i:i+chunk_size]
                    self.serial_conn.write(chunk)
                    
                    # 更新进度
                    progress = min(100, (i + len(chunk)) / file_size * 100)
                    self.root.after(0, lambda: self.update_progress(progress))
                    
                    time.sleep(0.02)  # 资源传输可能较慢
                
                # 发送结束命令
                self.serial_conn.write(b'RESOURCE_END\n')
                
            return True
        except Exception as e:
            self.log(f"资源烧录错误: {str(e)}")
            return False
    
    def flash_complete(self):
        """烧录完成后的清理工作"""
        self.is_flashing = False
        self.root.after(0, lambda: self.flash_btn.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.connect_btn.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.update_progress(0))
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress['value'] = value
        self.progress_label['text'] = f"{int(value)}%"
    
    def log(self, message):
        """添加日志信息"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.root.after(0, lambda: self.log_text.insert(tk.END, log_message))
        self.root.after(0, lambda: self.log_text.see(tk.END))
    
    def run(self):
        """运行应用程序"""
        self.root.mainloop()

if __name__ == "__main__":
    # 安装所需库
    try:
        import serial
        import serial.tools.list_ports
    except ImportError:
        print("请安装 pyserial: pip install pyserial")
        exit(1)
    
    app = AdvancedSerialFlasher()
    app.run()
