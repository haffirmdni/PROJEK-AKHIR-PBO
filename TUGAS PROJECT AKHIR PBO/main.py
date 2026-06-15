import sys
import sqlite3
from datetime import datetime
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QHeaderView, QFileDialog
from kasir import Ui_MainWindow

class CartModel:
    """Model untuk menyimpan data keranjang"""
    def __init__(self):
        self.items = []
    
    def add_item(self, kode, nama, harga, jumlah, stok_tersedia):
        # Cek stok
        if jumlah > stok_tersedia:
            return False, f"Stok tidak mencukupi! Stok tersedia: {stok_tersedia}"
        
        # Cek apakah barang sudah ada di keranjang
        for i, item in enumerate(self.items):
            if item['kode'] == kode:
                if item['jumlah'] + jumlah > stok_tersedia:
                    return False, f"Total melebihi stok! Stok tersedia: {stok_tersedia}"
                self.items[i]['jumlah'] += jumlah
                self.items[i]['subtotal'] = self.items[i]['jumlah'] * harga
                return True, "Barang berhasil ditambahkan"
        
        self.items.append({
            'kode': kode,
            'nama': nama,
            'harga': harga,
            'jumlah': jumlah,
            'subtotal': harga * jumlah
        })
        return True, "Barang berhasil ditambahkan"
    
    def get_all_items(self):
        return [(item['nama'], item['harga'], item['jumlah'], item['subtotal']) for item in self.items]
    
    def get_items_with_kode(self):
        return self.items.copy()
    
    def get_subtotal(self):
        return sum(item['subtotal'] for item in self.items)
    
    def clear(self):
        self.items = []
    
    def is_empty(self):
        return len(self.items) == 0

class MainApp(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        # Inisialisasi database
        self.init_database()
        
        # Inisialisasi cart model
        self.cart_model = CartModel()
        
        # Daftar barang untuk autocomplete
        self.barang_list = []
        self.load_barang_list()
        
        # Setup autocomplete untuk txtNamaBarang
        self.setup_autocomplete()
        
        # Variabel untuk menyimpan data barang yang dipilih
        self.current_barang = None
        
        # Koneksi signal-slot untuk tab Kasir
        self.btnTambah.clicked.connect(self.tambah_ke_keranjang)
        self.btnReset.clicked.connect(self.reset_keranjang)
        self.spinDiskon.valueChanged.connect(self.update_ringkasan)
        self.btnHitung.clicked.connect(self.hitung_kembalian)
        self.btnCetak.clicked.connect(self.cetak_struk)
        self.txtNamaBarang.textChanged.connect(self.cari_harga_barang)
        
        # Koneksi signal-slot untuk tab Manajemen Stok
        self.btnTambahBarang.clicked.connect(self.tambah_barang)
        self.btnEditBarang.clicked.connect(self.edit_barang)
        self.btnHapusBarang.clicked.connect(self.hapus_barang)
        self.btnClearBarang.clicked.connect(self.clear_form_barang)
        self.tblBarang.itemSelectionChanged.connect(self.load_selected_barang)
        
        # Setup tabel
        self.setup_tabel_keranjang()
        self.load_tabel_barang()
        
        # Inisialisasi label
        self.update_ringkasan()
        self.lblKembali.setText("")
        
    def parse_currency(self, text):
        """Parse currency string to integer"""
        if not text:
            return 0
        return int(text.replace(",", "").replace("Rp", "").strip())
    
    def format_currency(self, value):
        """Format integer to currency string with dot as thousand separator"""
        return f"{value:,.0f}".replace(",", ".")
    
    def init_database(self):
        """Inisialisasi database SQLite"""
        self.conn = sqlite3.connect('toko.db')
        self.cursor = self.conn.cursor()
        
        # Create table barang if not exists
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS barang (
                kode TEXT PRIMARY KEY,
                nama TEXT NOT NULL,
                harga INTEGER NOT NULL,
                stok INTEGER NOT NULL DEFAULT 0
            )
        ''')
        
        # Insert sample data if table is empty
        self.cursor.execute("SELECT COUNT(*) FROM barang")
        if self.cursor.fetchone()[0] == 0:
            sample_data = [
                ('B001', 'Buku Tulis', 3000, 50),
                ('B002', 'Pensil', 1000, 100),
                ('B003', 'Penggaris', 4000, 75),
                ('B004', 'Buku Gambar', 4000, 60),
                ('B005', 'Penghapus', 2000, 200),
                ('B006', 'Rautan', 3000, 150),
                ('B007', 'Spidol', 8000, 120),
                ('B008', 'Kertas HVS', 25000, 40),
            ]
            self.cursor.executemany(
                "INSERT INTO barang (kode, nama, harga, stok) VALUES (?, ?, ?, ?)",
                sample_data
            )
            self.conn.commit()
    
    def load_barang_list(self):
        """Load daftar barang dari database untuk autocomplete"""
        self.cursor.execute("SELECT nama, harga, stok, kode FROM barang WHERE stok > 0")
        self.barang_list = self.cursor.fetchall()
    
    def setup_autocomplete(self):
        """Setup autocomplete untuk input nama barang"""
        completer = QtWidgets.QCompleter([b[0] for b in self.barang_list])
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.txtNamaBarang.setCompleter(completer)
    
    def cari_harga_barang(self):
        """Mencari harga barang berdasarkan nama yang diinput"""
        nama = self.txtNamaBarang.text().strip()
        if nama:
            # Cari barang yang namanya mengandung teks input
            self.cursor.execute(
                "SELECT kode, nama, harga, stok FROM barang WHERE nama LIKE ? AND stok > 0 LIMIT 1",
                (f"%{nama}%",)
            )
            result = self.cursor.fetchone()
            if result:
                kode, nama_lengkap, harga, stok = result
                self.txtHarga.setText(f"Rp {self.format_currency(harga)}")
                self.current_barang = {
                    'kode': kode,
                    'nama': nama_lengkap,
                    'harga': harga,
                    'stok': stok
                }
            else:
                self.txtHarga.clear()
                self.current_barang = None
        else:
            self.txtHarga.clear()
            self.current_barang = None
    
    def setup_tabel_keranjang(self):
        """Setup tabel keranjang belanja"""
        headers = ["Barang", "Harga", "Jumlah", "Subtotal"]
        self.tblKeranjang.setHorizontalHeaderLabels(headers)
        self.tblKeranjang.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tblKeranjang.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tblKeranjang.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tblKeranjang.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
    
    def tambah_ke_keranjang(self):
        """Tambah barang ke keranjang"""
        if not self.current_barang:
            QMessageBox.warning(self, "Peringatan", "Silakan pilih barang yang valid!")
            return
        
        jumlah = self.spinJumlah.value()
        
        success, message = self.cart_model.add_item(
            self.current_barang['kode'],
            self.current_barang['nama'],
            self.current_barang['harga'],
            jumlah,
            self.current_barang['stok']
        )
        
        if success:
            # Update tampilan keranjang
            self.update_tabel_keranjang()
            self.update_ringkasan()
            
            # Reset kembalian label setelah keranjang berubah
            self.lblKembali.setText("")
            
            # Reset input
            self.txtNamaBarang.clear()
            self.spinJumlah.setValue(1)
            self.txtHarga.clear()
            self.current_barang = None
        else:
            QMessageBox.warning(self, "Peringatan", message)
    
    def update_tabel_keranjang(self):
        """Update tampilan tabel keranjang"""
        items = self.cart_model.get_all_items()
        self.tblKeranjang.setRowCount(len(items))
        
        for row, (nama, harga, jumlah, subtotal) in enumerate(items):
            self.tblKeranjang.setItem(row, 0, QTableWidgetItem(nama))
            self.tblKeranjang.setItem(row, 1, QTableWidgetItem(f"Rp {self.format_currency(harga)}"))
            self.tblKeranjang.setItem(row, 2, QTableWidgetItem(str(jumlah)))
            self.tblKeranjang.setItem(row, 3, QTableWidgetItem(f"Rp {self.format_currency(subtotal)}"))
    
    def update_ringkasan(self):
        """Update ringkasan transaksi"""
        subtotal = self.cart_model.get_subtotal()
        
        # Hitung diskon
        diskon_persen = self.spinDiskon.value()
        diskon_rp = int(subtotal * diskon_persen / 100)
        
        # Hitung pajak 10% setelah diskon
        setelah_diskon = subtotal - diskon_rp
        pajak = int(setelah_diskon * 10 / 100)
        
        # Total akhir
        total = setelah_diskon + pajak
        
        # Update label
        self.lblSubtotal.setText(f"Rp {self.format_currency(subtotal)}")
        self.lblDiskon.setText(f"Rp {self.format_currency(diskon_rp)}")
        self.lblPajak.setText(f"Rp {self.format_currency(pajak)}")
        self.lblTotal.setText(f"Rp {self.format_currency(total)}")
    
    def hitung_kembalian(self):
        """Hitung kembalian - hanya ketika tombol diklik"""
        if self.cart_model.is_empty():
            QMessageBox.warning(self, "Peringatan", "Keranjang masih kosong!")
            return
        
        try:
            tunai = self.parse_currency(self.txtTunai.text())
            if tunai == 0 and not self.txtTunai.text():
                QMessageBox.warning(self, "Peringatan", "Silakan masukkan nominal tunai!")
                return
            
            subtotal = self.cart_model.get_subtotal()
            diskon_persen = self.spinDiskon.value()
            diskon_rp = int(subtotal * diskon_persen / 100)
            setelah_diskon = subtotal - diskon_rp
            pajak = int(setelah_diskon * 10 / 100)
            total = setelah_diskon + pajak
            
            if tunai < total:
                kekurangan = total - tunai
                self.lblKembali.setText(f"Kurang Rp {self.format_currency(kekurangan)}")
                self.lblKembali.setStyleSheet("color: red; font-size:14pt; font-weight:bold;")
            else:
                kembalian = tunai - total
                self.lblKembali.setText(f"Rp {self.format_currency(kembalian)}")
                self.lblKembali.setStyleSheet("color: green; font-size:14pt; font-weight:bold;")
        except ValueError:
            QMessageBox.warning(self, "Peringatan", "Nominal tunai harus berupa angka!")
            self.lblKembali.setText("")
    
    def reset_keranjang(self):
        """Reset keranjang belanja"""
        self.cart_model.clear()
        self.update_tabel_keranjang()
        self.spinDiskon.setValue(0)
        self.txtTunai.clear()
        self.update_ringkasan()
        self.lblKembali.setText("")
    
    def cetak_struk(self):
        """Generate receipt text and save to file"""
        if self.cart_model.is_empty():
            QMessageBox.warning(self, "Peringatan", "Keranjang kosong!")
            return
        
        # Cek apakah kembalian sudah dihitung
        if not self.lblKembali.text():
            reply = QMessageBox.question(self, "Konfirmasi", 
                "Belum menghitung kembalian. Lanjutkan cetak struk?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        now = datetime.now()
        subtotal = self.cart_model.get_subtotal()
        diskon_persen = self.spinDiskon.value()
        diskon_rp = subtotal * (diskon_persen / 100)
        pajak = (subtotal - diskon_rp) * 0.10
        total = subtotal - diskon_rp + pajak
        tunai = self.parse_currency(self.txtTunai.text())
        kembali = tunai - total
        
        # Cek apakah semua barang tersedia di stok
        items_with_kode = self.cart_model.get_items_with_kode()
        for item in items_with_kode:
            self.cursor.execute("SELECT stok FROM barang WHERE kode = ?", (item['kode'],))
            stok_tersedia = self.cursor.fetchone()[0]
            if item['jumlah'] > stok_tersedia:
                QMessageBox.warning(self, "Peringatan", 
                    f"Stok {item['nama']} tidak mencukupi!\n"
                    f"Diminta: {item['jumlah']}, Tersedia: {stok_tersedia}")
                return
        
        # Generate receipt
        receipt = []
        receipt.append("=" * 45)
        receipt.append("TOKO SEMOGA NILAI A".center(45))
        receipt.append("Jl. UMS JAYA No. 1423".center(45))
        receipt.append("Telp: 088 123 456 789".center(45))
        receipt.append("=" * 45)
        receipt.append(f"Tgl: {now.strftime('%d/%m/%Y %H:%M:%S')}")
        receipt.append("-" * 45)
        receipt.append(f"{'Nama Barang':<18} {'Harga':>9} {'Qty':>4} {'Subtotal':>9}")
        receipt.append("-" * 45)
        
        for item in self.cart_model.get_all_items():
            nama = item[0][:18]
            harga = item[1]
            jumlah = item[2]
            subtotal_item = item[3]
            receipt.append(f"{nama:<18} Rp{harga:>7,.0f} {jumlah:>3} Rp{subtotal_item:>8,.0f}")
        
        receipt.append("-" * 45)
        receipt.append(f"{'Subtotal':<30}   Rp{subtotal:>9,.0f}")
        receipt.append(f"{'Diskon':<30}   Rp{diskon_rp:>9,.0f}")
        receipt.append(f"{'Pajak (10%)':<30}   Rp{pajak:>9,.0f}")
        receipt.append("-" * 45)
        receipt.append(f"{'TOTAL':<30}   Rp{total:>9,.0f}")
        receipt.append(f"{'Tunai':<30}   Rp{tunai:>9,.0f}")
        receipt.append(f"{'Kembali':<30}   Rp{kembali:>9,.0f}")
        receipt.append("=" * 45)
        receipt.append("TERIMA KASIH".center(45))
        receipt.append("Barang yang sudah dibeli".center(45))
        receipt.append("tidak dapat dikembalikan".center(45))
        receipt.append("=" * 45)
        
        # Replace comma with dot for thousand separator in display
        receipt_text = "\n".join(receipt).replace(",", ".")
        
        # Tampilkan di textStruk
        self.textStruk.setText(receipt_text)
        
        # Kurangi stok
        for item in items_with_kode:
            self.cursor.execute(
                "UPDATE barang SET stok = stok - ? WHERE kode = ?",
                (item['jumlah'], item['kode'])
            )
        self.conn.commit()
        
        # Simpan ke file txt
        try:
            # Buat nama file dengan timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"struk_{timestamp}.txt"
            
            # Tanya user apakah ingin menyimpan dengan nama custom
            reply = QMessageBox.question(self, "Simpan Struk", 
                f"Apakah ingin menyimpan struk ke file?\nNama default: {filename}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
            
            if reply == QMessageBox.StandardButton.Yes:
                # Simpan dengan nama default
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(receipt_text)
                QMessageBox.information(self, "Sukses", f"Struk berhasil disimpan ke:\n{filename}")
                
            elif reply == QMessageBox.StandardButton.No:
                # Pilih lokasi dan nama file sendiri
                file_path, _ = QFileDialog.getSaveFileName(
                    self, 
                    "Simpan Struk", 
                    f"struk_{timestamp}.txt", 
                    "Text Files (*.txt);;All Files (*)"
                )
                if file_path:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(receipt_text)
                    QMessageBox.information(self, "Sukses", f"Struk berhasil disimpan ke:\n{file_path}")
            
            # Reload stok dan reset keranjang
            self.load_tabel_barang()
            self.load_barang_list()
            self.setup_autocomplete()
            self.reset_keranjang()
            
            QMessageBox.information(self, "Sukses", "Transaksi berhasil!\nStok telah diperbarui.")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Gagal menyimpan struk: {str(e)}")
    
    # ==================== MANAJEMEN STOK ====================
    
    def load_tabel_barang(self):
        """Load data barang ke tabel manajemen stok"""
        self.cursor.execute("SELECT kode, nama, harga, stok FROM barang ORDER BY kode")
        barang = self.cursor.fetchall()
        
        self.tblBarang.setRowCount(len(barang))
        for row, (kode, nama, harga, stok) in enumerate(barang):
            self.tblBarang.setItem(row, 0, QTableWidgetItem(kode))
            self.tblBarang.setItem(row, 1, QTableWidgetItem(nama))
            self.tblBarang.setItem(row, 2, QTableWidgetItem(f"Rp {self.format_currency(harga)}"))
            self.tblBarang.setItem(row, 3, QTableWidgetItem(str(stok)))
    
    def tambah_barang(self):
        """Tambah barang baru"""
        kode = self.txtKode.text().strip()
        nama = self.txtNama.text().strip()
        harga = self.txtHargaStok.text().strip()
        stok = self.spinStok.value()
        
        if not kode or not nama or not harga:
            QMessageBox.warning(self, "Peringatan", "Kode, Nama, dan Harga harus diisi!")
            return
        
        try:
            harga = int(harga.replace(",", ""))
        except ValueError:
            QMessageBox.warning(self, "Peringatan", "Harga harus berupa angka!")
            return
        
        try:
            self.cursor.execute(
                "INSERT INTO barang (kode, nama, harga, stok) VALUES (?, ?, ?, ?)",
                (kode, nama, harga, stok)
            )
            self.conn.commit()
            QMessageBox.information(self, "Sukses", "Barang berhasil ditambahkan!")
            self.load_tabel_barang()
            self.load_barang_list()
            self.setup_autocomplete()
            self.clear_form_barang()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Peringatan", "Kode barang sudah ada!")
    
    def edit_barang(self):
        """Edit barang yang dipilih"""
        current_row = self.tblBarang.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Peringatan", "Pilih barang yang akan diedit!")
            return
        
        kode_lama = self.tblBarang.item(current_row, 0).text()
        kode_baru = self.txtKode.text().strip()
        nama = self.txtNama.text().strip()
        harga = self.txtHargaStok.text().strip()
        stok = self.spinStok.value()
        
        if not nama or not harga:
            QMessageBox.warning(self, "Peringatan", "Nama dan Harga harus diisi!")
            return
        
        try:
            harga = int(harga.replace(",", ""))
        except ValueError:
            QMessageBox.warning(self, "Peringatan", "Harga harus berupa angka!")
            return
        
        try:
            if kode_lama == kode_baru:
                self.cursor.execute(
                    "UPDATE barang SET nama = ?, harga = ?, stok = ? WHERE kode = ?",
                    (nama, harga, stok, kode_lama)
                )
            else:
                # Cek kode baru apakah sudah ada
                self.cursor.execute("SELECT kode FROM barang WHERE kode = ?", (kode_baru,))
                if self.cursor.fetchone():
                    QMessageBox.warning(self, "Peringatan", "Kode barang sudah ada!")
                    return
                self.cursor.execute(
                    "UPDATE barang SET kode = ?, nama = ?, harga = ?, stok = ? WHERE kode = ?",
                    (kode_baru, nama, harga, stok, kode_lama)
                )
            
            self.conn.commit()
            QMessageBox.information(self, "Sukses", "Barang berhasil diedit!")
            self.load_tabel_barang()
            self.load_barang_list()
            self.setup_autocomplete()
            self.clear_form_barang()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Gagal mengedit barang: {str(e)}")
    
    def hapus_barang(self):
        """Hapus barang yang dipilih"""
        current_row = self.tblBarang.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Peringatan", "Pilih barang yang akan dihapus!")
            return
        
        kode = self.tblBarang.item(current_row, 0).text()
        nama = self.tblBarang.item(current_row, 1).text()
        
        reply = QMessageBox.question(self, "Konfirmasi", 
            f"Yakin ingin menghapus barang '{nama}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.cursor.execute("DELETE FROM barang WHERE kode = ?", (kode,))
            self.conn.commit()
            QMessageBox.information(self, "Sukses", "Barang berhasil dihapus!")
            self.load_tabel_barang()
            self.load_barang_list()
            self.setup_autocomplete()
            self.clear_form_barang()
    
    def load_selected_barang(self):
        """Load data barang yang dipilih ke form"""
        current_row = self.tblBarang.currentRow()
        if current_row >= 0:
            kode = self.tblBarang.item(current_row, 0).text()
            nama = self.tblBarang.item(current_row, 1).text()
            harga = self.tblBarang.item(current_row, 2).text().replace("Rp ", "").replace(".", "")
            stok = self.tblBarang.item(current_row, 3).text()
            
            self.txtKode.setText(kode)
            self.txtNama.setText(nama)
            self.txtHargaStok.setText(harga)
            self.spinStok.setValue(int(stok))
    
    def clear_form_barang(self):
        """Clear form input barang"""
        self.txtKode.clear()
        self.txtNama.clear()
        self.txtHargaStok.clear()
        self.spinStok.setValue(0)
        self.tblBarang.clearSelection()
    
    def closeEvent(self, event):
        """Tutup koneksi database saat aplikasi ditutup"""
        self.conn.close()
        event.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())