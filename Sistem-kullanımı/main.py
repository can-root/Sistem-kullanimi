import sys
import psutil
import platform
import GPUtil
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QTabWidget,
                             QLineEdit, QPushButton, QMessageBox)
from PyQt5.QtGui import QPainter, QColor, QPalette
from PyQt5.QtCore import QTimer

KURAL_DOSYASI = 'kural.json'

class GrafikWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setAutoFillBackground(True)
        self.setPalette(QPalette(QColor(50, 50, 50)))  

        self.cpu_kullanimi = 0
        self.ram_kullanimi = 0
        self.disk_kullanimi = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.guncelle)
        self.timer.start(1000)  

    def guncelle(self):
        self.cpu_kullanimi = psutil.cpu_percent()
        ram = psutil.virtual_memory()
        self.ram_kullanimi = ram.percent
        disk = psutil.disk_usage('/')
        self.disk_kullanimi = disk.percent
        self.update()  

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        self.cizim(painter, self.cpu_kullanimi, 50, "CPU Kullanımı")
        self.cizim(painter, self.ram_kullanimi, 200, "RAM Kullanımı")
        self.cizim(painter, self.disk_kullanimi, 350, "Disk Kullanımı")

    def cizim(self, painter, deger, x_pos, baslik):
        color = self.hesapla_renk(deger)
        painter.setBrush(color)

        yükseklik = int(deger * 3)
        painter.drawRect(x_pos, 400 - yükseklik, 30, yükseklik) 
        painter.drawText(x_pos, 420, f"{baslik}: {deger}%") 

    def hesapla_renk(self, deger):
        if deger >= 100:
            return QColor(255, 0, 0) 
        elif deger <= 0:
            return QColor(0, 255, 0)  
        else:
            red = int(255 * (deger / 100))
            green = int(255 * (1 - deger / 100))
            return QColor(red, green, 0)

class CihazBilgileriWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.bilgi_yazilari()

    def bilgi_yazilari(self):
        self.layout.addWidget(QLabel(f"İşletim Sistemi: {platform.system()} {platform.release()}"))
        self.layout.addWidget(QLabel(f"Cihaz Adı: {platform.node()}"))
        self.layout.addWidget(QLabel(f"RAM: {self.get_ram_bilgisi():.2f} GB"))  
        self.layout.addWidget(QLabel(f"Disk: {self.get_disk_bilgisi():.2f} GB"))  
        self.layout.addWidget(QLabel(f"Ekran Kartı: {self.get_ekran_kartları()}"))

    def get_ram_bilgisi(self):
        return psutil.virtual_memory().total / (1024 ** 3)

    def get_disk_bilgisi(self):
        return psutil.disk_usage('/').total / (1024 ** 3)

    def get_ekran_kartları(self):
        gpus = GPUtil.getGPUs()
        return ', '.join([gpu.name for gpu in gpus]) if gpus else "Bilinmiyor"

class KurallarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QLabel("<b>Maksimum Kullanım Limitleri (Yüzde)</b>"))  

        self.cpu_limit_input = QLineEdit(self)
        self.ram_limit_input = QLineEdit(self)

        self.layout.addWidget(QLabel("Maksimum CPU:"))
        self.layout.addWidget(self.cpu_limit_input)

        self.layout.addWidget(QLabel("Maksimum RAM:"))
        self.layout.addWidget(self.ram_limit_input)

        self.save_button = QPushButton("Kaydet", self)
        self.save_button.clicked.connect(self.kaydet)
        self.layout.addWidget(self.save_button)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.kontrol_et)
        self.timer.start(5000)  
        self.kurallari_yukle()

    def kurallari_yukle(self):
        try:
            with open(KURAL_DOSYASI, 'r') as f:
                kurallar = json.load(f)
                self.cpu_limit_input.setText(str(kurallar.get('max_cpu', '0')))
                self.ram_limit_input.setText(str(kurallar.get('max_ram', '0')))
        except (FileNotFoundError, json.JSONDecodeError):
            self.cpu_limit_input.setText("0")
            self.ram_limit_input.setText("0")

    def kaydet(self):
        try:
            max_cpu = int(self.cpu_limit_input.text())
            max_ram = int(self.ram_limit_input.text())

            with open(KURAL_DOSYASI, 'w') as f:
                json.dump({'max_cpu': max_cpu, 'max_ram': max_ram}, f)

            QMessageBox.information(self, "Başarılı", "Kullanım limitleri kaydedildi.")
        except ValueError:
            QMessageBox.warning(self, "Hata", "Lütfen geçerli bir sayı girin.")

    def kontrol_et(self):
        try:
            with open(KURAL_DOSYASI, 'r') as f:
                kurallar = json.load(f)
                max_cpu = kurallar.get('max_cpu', 0)
                max_ram = kurallar.get('max_ram', 0)

                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    try:
                        cpu_usage = proc.info['cpu_percent']
                        ram_usage = proc.info['memory_percent']
                        if cpu_usage > max_cpu or ram_usage > max_ram:
                            proc.kill()
                            print(f"{proc.info['name']} (PID: {proc.info['pid']}) sonlandırıldı.")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
        except (FileNotFoundError, json.JSONDecodeError):
            pass  

class AnaPencere(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistem Kullanımı Grafikleri ve Cihaz Bilgileri")
        self.setGeometry(100, 100, 600, 480)

        # Tab widget oluştur
        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        # Widget'ları ekleyin
        self.grafik_widget = GrafikWidget()
        self.cihaz_bilgileri_widget = CihazBilgileriWidget()
        self.kurallar_widget = KurallarWidget()

        self.tabs.addTab(self.grafik_widget, "Sistem Kullanımı")
        self.tabs.addTab(self.cihaz_bilgileri_widget, "Cihaz Bilgileri")
        self.tabs.addTab(self.kurallar_widget, "Kurallar")

if __name__ == '__main__':
    app = QApplication(sys.argv)

    try:
        import psutil
        import GPUtil
    except ImportError:
        print("Gerekli kütüphaneler yüklü değil. Lütfen yükleyin: pip install psutil GPUtil")
        sys.exit(1)

    pencere = AnaPencere()
    pencere.show()
    sys.exit(app.exec_())
