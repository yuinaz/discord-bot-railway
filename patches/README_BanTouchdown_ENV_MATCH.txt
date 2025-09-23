Ban Touchdown — ENV-MATCH (LOG only)
------------------------------------
Disetel agar **persis mengikuti ENV kamu** (hanya LOG_CHANNEL_ID / LOG_CHANNEL_ID_RAW).
Tidak menggunakan BAN_PUBLIC_*.

Perilaku:
1) Simpan "last seen" user di **TextChannel** (thread diabaikan).
2) Saat ban:
   - Kirim embed ke **TextChannel** tempat user terakhir terlihat (jika bot bisa kirim).
   - Kirim embed ke **LOG channel** dari ENV kamu.
   - Dedup ringan terhadap mod-log (5s).

Tidak ada variabel ENV baru.
Izin:
- LOG channel: View + Send
- Channel umum (touchdown): View + Send
