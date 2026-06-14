import sys
import re
import sqlite3
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from datetime import datetime
from kasir import Ui_MainWindow


class CartTableModel(QAbstractTableModel):
    def __init__(self, data=[], headers=["Nama Barang", "Harga", "Jumlah", "Subtotal"]):
        super().__init__()
        self._data = data
        self._headers = headers

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        
        if role == Qt.ItemDataRole.DisplayRole:
            value = self._data[row][col]
            if col == 1 or col == 3:  # Harga or Subtotal column
                return f"Rp {value:,.0f}".replace(",", ".")
            elif col == 2:  # Jumlah column
                return str(value)
            else:
                return value
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [1, 2, 3]:
                return Qt.AlignmentFlag.AlignRight.value
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section]
        return None

    def add_item(self, item):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self._data.append(item)
        self.endInsertRows()

    def remove_item(self, row):
        if 0 <= row < self.rowCount():
            self.beginRemoveRows(QModelIndex(), row, row)
            self._data.pop(row)
            self.endRemoveRows()

    def clear_items(self):
        self.beginResetModel()
        self._data.clear()
        self.endResetModel()

    def get_all_items(self):
        return self._data.copy()

    def get_subtotal(self):
        return sum(item[3] for item in self._data)


class CashierApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.load_barang()
        self.tampil_harga()
        self.tampil_barang()
            
        self.ui.cmbBarang.currentTextChanged.connect(self.tampil_harga)
        self.ui.btnTambahBarang.clicked.connect(self.tambah_barang)
        
        # Initialize cart model
        self.cart_model = CartTableModel()
        self.ui.lblkeranjang.setModel(self.cart_model)
        
        # Configure table
        self.ui.lblkeranjang.setColumnWidth(0, 200)
        self.ui.lblkeranjang.setColumnWidth(1, 120)
        self.ui.lblkeranjang.setColumnWidth(2, 80)
        self.ui.lblkeranjang.setColumnWidth(3, 120)
        
        # Connect signals
        self.ui.btnTambah.clicked.connect(self.add_to_cart)
        self.ui.btnReset.clicked.connect(self.reset_cart)
        self.ui.btnHitungkembali.clicked.connect(self.calculate_change)
        self.ui.btnCetak.clicked.connect(self.print_receipt)
        self.ui.spinDiskon.valueChanged.connect(self.update_summary)
        self.ui.txtHarga.textChanged.connect(self.format_harga_input)
        self.ui.txtTunai.textChanged.connect(self.format_tunai_input)
        
        # Connect cart changes to update summary
        self.cart_model.rowsInserted.connect(self.on_cart_changed)
        self.cart_model.rowsRemoved.connect(self.on_cart_changed)
        self.cart_model.modelReset.connect(self.on_cart_changed)
        
        # Enable delete key
        self.ui.lblkeranjang.keyPressEvent = self.table_key_press_event
        
        # Initialize
        self.update_summary()
        
    def format_harga_input(self):
        """Format harga input dengan pemisah ribuan"""
        text = self.ui.txtHarga.text()
        # Remove non-digit characters
        digits = re.sub(r'[^0-9]', '', text)
        if digits:
            # Format with thousand separators
            formatted = "{:,.0f}".format(int(digits)).replace(",", ".")
            self.ui.txtHarga.blockSignals(True)
            self.ui.txtHarga.setText(formatted)
            self.ui.txtHarga.blockSignals(False)
            # Move cursor to end
            self.ui.txtHarga.setCursorPosition(len(formatted))
    
    def format_tunai_input(self):
        """Format tunai input dengan pemisah ribuan"""
        text = self.ui.txtTunai.text()
        digits = re.sub(r'[^0-9]', '', text)
        if digits:
            formatted = "{:,.0f}".format(int(digits)).replace(",", ".")
            self.ui.txtTunai.blockSignals(True)
            self.ui.txtTunai.setText(formatted)
            self.ui.txtTunai.blockSignals(False)
            self.ui.txtTunai.setCursorPosition(len(formatted))
    
    def parse_currency(self, text):
        """Parse currency string to integer"""
        if not text:
            return 0
        clean = re.sub(r'[^0-9]', '', text)
        return int(clean) if clean else 0
    
    def add_to_cart(self):
        """Add item to cart"""
        nama_barang = self.ui.cmbBarang.currentText()
        harga_str = self.ui.txtHarga.text()
        jumlah = self.ui.spinJumlah.value()
        
        if not nama_barang:
            QtWidgets.QMessageBox.warning(self, "Peringatan", "Nama barang tidak boleh kosong!")
            return
        
        harga = self.parse_currency(harga_str)
        
        if harga <= 0:
            QtWidgets.QMessageBox.warning(self, "Peringatan", "Harga harus lebih dari 0!")
            return
        
        subtotal = harga * jumlah
        
        # Add to cart
        item = [nama_barang, harga, jumlah, subtotal]
        self.cart_model.add_item(item)
        
        # Clear input fields
        self.ui.cmbBarang.setCurrentIndex(0)
        self.ui.txtHarga.clear()
        self.ui.spinJumlah.setValue(1)
        self.ui.cmbBarang.setFocus()
        
        self.statusBar().showMessage(f"{nama_barang} ditambahkan ke keranjang", 2000)
    
    def remove_from_cart(self, row):
        """Remove item from cart"""
        item = self.cart_model._data[row]
        self.cart_model.remove_item(row)
        self.statusBar().showMessage(f"{item[0]} dihapus dari keranjang", 2000)
    
    def reset_cart(self):
        """Reset entire cart"""
        if self.cart_model.rowCount() > 0:
            reply = QtWidgets.QMessageBox.question(
                self, 
                "Konfirmasi", 
                "Apakah Anda yakin ingin menghapus semua item dari keranjang?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.cart_model.clear_items()
                self.ui.spinDiskon.setValue(0)
                self.ui.txtTunai.clear()
                self.ui.lblKembali.setText("")
                self.ui.textStruk.clear()
                self.statusBar().showMessage("Keranjang telah direset", 2000)
    
    def on_cart_changed(self):
        """Update summary when cart changes"""
        self.update_summary()
    
    def update_summary(self):
        """Update subtotal, discount, tax, and total"""
        subtotal = self.cart_model.get_subtotal()
        
        # Calculate discount
        diskon_persen = self.ui.spinDiskon.value()
        diskon_rp = subtotal * (diskon_persen / 100)
        
        # Calculate tax (10% after discount)
        pajak = (subtotal - diskon_rp) * 0.10
        
        # Calculate total
        total = subtotal - diskon_rp + pajak
        
        # Update labels
        self.ui.lblSubTotal.setText(f"Rp {subtotal:,.0f}".replace(",", "."))
        self.ui.lblDiskonRp.setText(f"Rp {diskon_rp:,.0f}".replace(",", "."))
        self.ui.lblPajak.setText(f"Rp {pajak:,.0f}".replace(",", "."))
        self.ui.lblTotal.setText(f"Rp {total:,.0f}".replace(",", "."))
        
        return total
    
    def calculate_change(self):
        """Calculate change based on cash given"""
        total = self.update_summary()
        tunai_str = self.ui.txtTunai.text()
        
        if not tunai_str:
            QtWidgets.QMessageBox.warning(self, "Peringatan", "Masukkan jumlah uang tunai!")
            return
        
        tunai = self.parse_currency(tunai_str)
        
        if tunai < total:
            kekurangan = total - tunai
            self.ui.lblKembali.setText(f"Kekurangan: Rp {kekurangan:,.0f}".replace(",", "."))
            self.ui.lblKembali.setStyleSheet("color: red; font-size: 12pt; font-weight: bold;")
            QtWidgets.QMessageBox.warning(
                self, 
                "Peringatan", 
                f"Uang kurang sebesar Rp {kekurangan:,.0f}".replace(",", ".")
            )
        else:
            kembali = tunai - total
            self.ui.lblKembali.setText(f"Kembali: Rp {kembali:,.0f}".replace(",", "."))
            self.ui.lblKembali.setStyleSheet("color: green; font-size: 12pt; font-weight: bold;")
            self.statusBar().showMessage(f"Kembalian: Rp {kembali:,.0f}".replace(",", "."), 3000)
            # Auto generate receipt preview
            self.generate_receipt_preview()
    
    def generate_receipt_preview(self):
        """Generate receipt preview without saving"""
        if self.cart_model.rowCount() == 0:
            return
        
        total = self.update_summary()
        tunai_str = self.ui.txtTunai.text()
        
        if not tunai_str:
            return
            
        tunai = self.parse_currency(tunai_str)
        
        if tunai < total:
            return
        
        receipt = self.generate_receipt_text()
        self.ui.textStruk.setText(receipt)
    
    def generate_receipt_text(self):
        """Generate receipt text"""
        now = datetime.now()
        subtotal = self.cart_model.get_subtotal()
        diskon_persen = self.ui.spinDiskon.value()
        diskon_rp = subtotal * (diskon_persen / 100)
        pajak = (subtotal - diskon_rp) * 0.10
        total = subtotal - diskon_rp + pajak
        tunai = self.parse_currency(self.ui.txtTunai.text())
        kembali = tunai - total
        
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
        return "\n".join(receipt).replace(",", ".")
    
    def print_receipt(self):
        """Print/save receipt"""
        if self.cart_model.rowCount() == 0:
            QtWidgets.QMessageBox.warning(self, "Peringatan", "Keranjang masih kosong!")
            return
        
        total = self.update_summary()
        tunai_str = self.ui.txtTunai.text()
        
        if not tunai_str:
            QtWidgets.QMessageBox.warning(self, "Peringatan", "Hitung kembalian terlebih dahulu!")
            return
        
        tunai = self.parse_currency(tunai_str)
        
        if tunai < total:
            QtWidgets.QMessageBox.warning(self, "Peringatan", "Uang belum mencukupi!")
            return
        
        receipt = self.generate_receipt_text()
        
        # Ask to save to file
        reply = QtWidgets.QMessageBox.question(
            self,
            "Cetak Struk",
            "Apakah ingin menyimpan struk ke file?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            filename = f"struk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(receipt)
            QtWidgets.QMessageBox.information(self, "Sukses", f"Struk disimpan sebagai {filename}")
    
    def table_key_press_event(self, event):
        """Handle delete key to remove selected row"""
        if event.key() == Qt.Key.Key_Delete:
            selected = self.ui.lblkeranjang.selectedIndexes()
            if selected:
                row = selected[0].row()
                self.remove_from_cart(row)
        else:
            QtWidgets.QTableView.keyPressEvent(self.ui.lblkeranjang, event)

    def load_barang(self):

        self.ui.cmbBarang.clear()

        conn = sqlite3.connect("kasir.db")
        cursor = conn.cursor()

        cursor.execute("SELECT nama FROM barang")

        data = cursor.fetchall()

        for row in data:
            self.ui.cmbBarang.addItem(row[0])

        conn.close()

    def tampil_harga(self):
        nama = self.ui.cmbBarang.currentText()

        conn = sqlite3.connect("kasir.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT harga FROM barang WHERE nama=?",
            (nama,)
        )

        hasil = cursor.fetchone()

        if hasil:
            self.ui.txtHarga.setText(str(hasil[0]))

        conn.close()

    def tampil_barang(self):

        conn = sqlite3.connect("kasir.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM barang")

        data = cursor.fetchall()

        self.ui.tableBarang.setRowCount(len(data))
        self.ui.tableBarang.setColumnCount(4)

        self.ui.tableBarang.setHorizontalHeaderLabels
        (["ID", "Nama Barang", "Harga", "Stok"])

        for row, row_data in enumerate(data):

         for col, value in enumerate(row_data):

            self.ui.tableBarang.setItem(
                row,
                col,
                QtWidgets.QTableWidgetItem(
                    str(value)
                )
            )

        conn.close()

    def tambah_barang(self):

        nama = self.ui.txtNamaBaru.text().strip()

        harga = self.ui.txtHargaBaru.text().strip()

        stok = self.ui.spinStok.value()

        if nama == "" or harga == "":
            QtWidgets.QMessageBox.warning(
            self,
            "Peringatan",
            "Data belum lengkap!"
        )
            return

        conn = sqlite3.connect("kasir.db")
        cursor = conn.cursor()

        cursor.execute(
             """INSERT INTO barang
                (nama,harga,stok)
                VALUES(?,?,?)
                """,
            (
                nama,
            int(harga),
            stok
        )
    )

        conn.commit()
        conn.close()

        self.tampil_barang()

        self.ui.txtNamaBaru.clear()
        self.ui.txtHargaBaru.clear()
        self.ui.spinStok.setValue(0)

        QtWidgets.QMessageBox.information(
        self,
        "Sukses",
        "Barang berhasil ditambahkan"
    )

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    window = CashierApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()