# ⚔ PIXEL BATTLE — LAN Multiplayer Fighter

Game chiến đấu pixel art 2 người qua mạng LAN, viết bằng Python + HTML.

## 🎮 Nhân Vật

| Nhân Vật | HP | ATK | DEF | SPD | Phong Cách |
|---|---|---|---|---|---|
| 🐉 Dragon Knight | 220 | 32 | 20 | 280 | Tank/Damage |
| 🔮 Shadow Mage | 150 | 48 | 8 | 310 | Burst Mage |
| ⚔️ Iron Warrior | 270 | 26 | 30 | 220 | Heavy Tank |
| 🌪️ Wind Ninja | 165 | 37 | 12 | 390 | Speed DPS |

## ⚡ Skills Mỗi Nhân Vật

**Dragon Knight:** 🔥 Dragon Breath (đốt cháy) · 🛡️ Dragon Scale (tăng DEF) · 💥 Sky Slam (choáng)

**Shadow Mage:** 🌀 Void Rift (xuyên giáp) · 💜 Soul Drain (hút máu) · ⚡ Shadow Nova (câm lặng)

**Iron Warrior:** 🛡️ Shield Bash (choáng) · 📣 War Cry (tăng ATK) · 💢 Ground Slam (làm chậm)

**Wind Ninja:** 🌟 Shuriken (nhanh) · 👥 Shadow Clone (né đòn) · 🌪️ Tornado (làm chậm)

## 🚀 Cài Đặt & Chạy

```bash
# 1. Cài thư viện
pip install flask flask-socketio

# 2. Chạy server (máy host)
python server.py

# 3. Server sẽ in ra IP LAN, ví dụ:
#    http://192.168.1.10:5000
```

## 🎮 Kết Nối

1. **Máy Host:** Chạy `python server.py`, xem IP LAN hiện ra
2. **Player 1:** Mở `http://localhost:5000` hoặc IP LAN
3. **Player 2:** Mở `http://<IP_host>:5000` (cùng mạng WiFi/LAN)
4. Cả 2 bấm **Kết Nối** → Chọn nhân vật → **CHIẾN!**

## ⌨️ Điều Khiển

| Phím | Hành Động |
|---|---|
| `A` | Đánh thường |
| `S` | Skill 1 |
| `D` | Skill 2 |
| `F` | Skill 3 |

Hoặc click trực tiếp vào các nút skill trên màn hình.

## 🎯 Logic Game

- **HP** khi về 0 → thua, đối thủ thắng
- **Energy** tự hồi 8/giây, dùng skill tốn energy
- **Cooldown:** đánh thường 0.8s, skill 2.5–14s tuỳ loại
- **Hiệu ứng:** Đốt cháy (burn tick 8 HP/lượt) · Choáng (stun skip lượt) · Làm chậm · Câm skill · Buff DEF/ATK · Né đòn
- **Crit:** 15% crit rate, x1.8 sát thương
- **Round timer:** 99 giây, hết giờ → so HP, ai nhiều hơn thắng

## 📁 Cấu Trúc File

```
pixelbattle/
├── server.py    ← Flask-SocketIO server
├── index.html   ← Game client (pixel art)
└── README.md    ← File này
```
