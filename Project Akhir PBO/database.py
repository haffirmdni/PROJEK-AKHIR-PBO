import sqlite3

conn = sqlite3.connect("kasir.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS barang(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT,
    harga INTEGER,
    stok INTEGER
)
""")

cursor.execute("""
INSERT INTO barang(nama,harga,stok)
VALUES
('Buku',3000,20),
('Pensil',2000,30),
('Penghapus',1000,15),
('Bolpoin',5000,25)
""")

conn.commit()
conn.close()

print("Database berhasil dibuat")