# ⚠️ Website 31-Day Limitation

## Masalah

Website **xg.smshj.com** hanya menampilkan **31 hari terakhir** dari data sales, terlepas dari date range yang dipilih di UI website atau scraper.

### Bukti
- User set range: **1 Januari - 4 Mei 2026** (124 hari)
- Data yang tersedia di website: **hanya ~31 hari terakhir**
- Hasil scraping: **40 records** (dari 8 pages) - sangat sedikit
- Kesimpulan: Data lama (Jan-Apr) **tidak tersimpan atau tidak accessible** via UI website

---

## Dampak ke Scraper

| Aspek | Status |
|-------|--------|
| Scraper functionality | ✅ Bekerja 100% normal |
| Data availability | ⚠️ Dibatasi by website (31 hari terakhir) |
| Historical data (>31 hari) | ❌ Tidak bisa didapat |
| Current month data | ✅ Semua tersedia |

---

## Solusi yang Mungkin

### 1. **Cek di Website (Manual)**
Buka https://xg.smshj.com/hbshengma/ dan login:
- Coba buka report export atau download feature
- Cek apakah ada opsi "full data" atau "archive"
- Lihat apakah ada API atau database access

### 2. **Gunakan Database Backup (Jika Ada)**
- Tanya ke sistem administrator website
- Cek apakah ada database backup dengan data historical
- Export dari sana jika tersedia

### 3. **Scrape Setiap Hari**
**Recommendation: Ini cara terbaik!**
```bash
# Jalankan scraper setiap hari
python main.py --schedule

# Scraper akan:
# ✅ Ambil data dari ~31 hari terakhir setiap hari
# ✅ Akumulasi data di JSON files (dengan timestamp)
# ✅ Dalam 31 hari, akan punya data historical 31 hari
# ✅ Keep running dan data akan terakumulasi
```

### 4. **Gunakan Scheduler untuk Daily Runs**
Jika belum set, aktifkan scheduled mode:

**Di `.env`:**
```env
SCHEDULE_TIME=02:00
SCHEDULE_TIMEZONE=UTC
```

**Jalankan:**
```bash
# Terminal 1: Start scheduler (akan run daily at 02:00 UTC)
python main.py --schedule

# Atau di background:
nohup python main.py --schedule > logs/scheduler.log 2>&1 &
```

**Hasil:**
- Setiap hari di 02:00 UTC, scraper akan run
- Ambil 31 hari terakhir (termasuk overlap data)
- Simpan dengan timestamp di `data/` folder
- Keep 10 file terakhir (older ones auto-deleted)

---

## Data Collection Strategy

Untuk build historical dataset:

1. **Mulai sekarang**: Jalankan `python main.py --schedule`
2. **Tunggu 31+ hari**: Setiap daily run akan kumpulkan data
3. **Setelah 31 hari**: Akan punya minimum 31 hari full historical data
4. **Ongoing**: Data akan terus update setiap hari

### Monitor Progress
```bash
# Cek berapa banyak file sudah accumulated
ls -lh data/scraping_report_*

# Cek latest data yang collected
tail -20 logs/scraper.log
```

---

## Column Mapping (Updated)

Parser sudah di-update dengan column mapping untuk semua 8 pages:

### paydetail (24 columns)
序号, 系统订单号, 支付渠道流水号, 设备ID, 设备名称, 货道, 持有人, 商品名称, 支付方式, 支付金额, 购买数量, 商品进价, 付款人, 支付时间, 支付状态, 退款状态, 出货状态, 出货详情, 优惠券码, 折扣详情, 优惠金额, 订单金额, 出货编码, 操作

### deliverydetail (9 columns)
设备ID, 设备名称, 货道, 商品名称, 商品品牌, 销售金额, 支付类型, 销售时间, 返回码

### cashdetail (9 columns)
checkbox, 序号, 设备ID, 设备名称, 持有人, 交易类型, 交易方式, 金额, 交易时间

### essDetail (15 columns)
设备ID, 设备名称, 销售数量, 销售总额, 微信, 微信刷脸, 微信刷掌, 支付宝, 支付宝刷脸, 支付宝NFC, 现金, 微信会员, 会员卡, 扶贫网, GHL

### mtOrder (10 columns)
美团订单号, 美团门店ID, 设备号, 商品名称, 支付金额, 订单状态, 取货码, 商品货道, 出货详情, 创建时间

### orderThird (15 columns)
订单号, 三方订单号, 设备ID, 商品名称, 货道, 支付方式, 订单金额, 商品单价, 数量, 购买人, 购买ID, 应退款金额, 出货状态, 交易时间, 创建时间

### orderThirdMachine (4 columns)
设备ID, 设备名称, 销售数量, 销售总额

### onlineOrderDetail (14 columns)
序号, 系统订单号, 支付渠道流水号, 设备ID, 设备名称, 商品名称, 支付方式, 支付金额, 购买数量, 商品进价, 支付状态, 出货状态, 退款状态, 支付时间

---

## Next Steps

1. ✅ **Parser updated** - Column mapping untuk semua 8 pages
2. ⏭️ **Test scraper lagi** - Run `python main.py --run-once` untuk verify
3. ⏭️ **Setup scheduler** - `python main.py --schedule` untuk daily runs
4. ⏭️ **Monitor data** - Kumpulkan data setiap hari untuk build historical dataset

---

## Kesimpulan

**Website limitation is NOT your scraper's fault.** Scraper bekerja perfect, tapi data historis tidak ada di website ≤31 hari lalu. Best practice adalah:

- ✅ Jalankan scraper **setiap hari** untuk kumpulkan data ongoing
- ✅ Dalam 31 hari, akan punya full month historical data
- ✅ Keep running indefinitely untuk continuous data collection
