"""
╔══════════════════════════════════════════════╗
║        PIXEL BATTLE - LAN Fighter           ║
║  Cài đặt: pip install flask flask-socketio  ║
║  Chạy:    python server.py                  ║
╚══════════════════════════════════════════════╝
"""

from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit, join_room
import random, time, os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pixelbattle_lan_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ══════════════════════════════════════════════
#  NHÂN VẬT & SKILL
# ══════════════════════════════════════════════
CHARACTERS = {
    'dragon_knight': {
        'name': 'Dragon Knight',
        'hp': 220, 'energy': 100, 'atk': 32, 'def': 20, 'spd': 280,
        'skills': [
            {'name': 'Dragon Breath', 'damage': 58, 'energy_cost': 15,
             'cooldown': 4.0, 'effect': 'burn', 'effect_dur': 3.0},
            {'name': 'Dragon Scale',  'damage': 0,  'energy_cost': 20,
             'cooldown': 8.0, 'effect': 'def_up', 'effect_dur': 5.0},
            {'name': 'Sky Slam',      'damage': 92, 'energy_cost': 30,
             'cooldown': 12.0, 'effect': 'stun', 'effect_dur': 1.5},
        ]
    },
    'shadow_mage': {
        'name': 'Shadow Mage',
        'hp': 150, 'energy': 160, 'atk': 48, 'def': 8, 'spd': 310,
        'skills': [
            {'name': 'Void Rift',   'damage': 68,  'energy_cost': 18,
             'cooldown': 4.5, 'effect': None, 'effect_dur': 0},
            {'name': 'Soul Drain',  'damage': 42,  'energy_cost': 25,
             'cooldown': 7.0, 'effect': 'lifesteal', 'effect_dur': 0},
            {'name': 'Shadow Nova', 'damage': 115, 'energy_cost': 40,
             'cooldown': 14.0, 'effect': 'silence', 'effect_dur': 2.0},
        ]
    },
    'iron_warrior': {
        'name': 'Iron Warrior',
        'hp': 270, 'energy': 80, 'atk': 26, 'def': 30, 'spd': 220,
        'skills': [
            {'name': 'Shield Bash',  'damage': 38, 'energy_cost': 15,
             'cooldown': 4.0, 'effect': 'stun', 'effect_dur': 1.2},
            {'name': 'War Cry',      'damage': 0,  'energy_cost': 22,
             'cooldown': 9.0, 'effect': 'atk_up', 'effect_dur': 6.0},
            {'name': 'Ground Slam',  'damage': 98, 'energy_cost': 35,
             'cooldown': 13.0, 'effect': 'slow', 'effect_dur': 3.0},
        ]
    },
    'wind_ninja': {
        'name': 'Wind Ninja',
        'hp': 165, 'energy': 125, 'atk': 37, 'def': 12, 'spd': 390,
        'skills': [
            {'name': 'Shuriken',     'damage': 48, 'energy_cost': 10,
             'cooldown': 2.5, 'effect': None, 'effect_dur': 0},
            {'name': 'Shadow Clone', 'damage': 64, 'energy_cost': 25,
             'cooldown': 7.0, 'effect': 'dodge', 'effect_dur': 2.0},
            {'name': 'Tornado',      'damage': 92, 'energy_cost': 35,
             'cooldown': 12.0, 'effect': 'slow', 'effect_dur': 3.5},
        ]
    },
}

# ══════════════════════════════════════════════
#  HẰNG SỐ GAME
# ══════════════════════════════════════════════
ENERGY_REGEN   = 8    # energy/giây
NORMAL_ATK_CD  = 0.8  # giây
BURN_DMG_TICK  = 8    # dmg mỗi tick burn
ROUND_TIME     = 99   # giây

# ══════════════════════════════════════════════
#  STATE MANAGEMENT
# ══════════════════════════════════════════════
rooms        = {}   # room_id → room_data
player_rooms = {}   # sid → room_id

def new_player_state(char_key):
    c = CHARACTERS[char_key]
    return {
        'char':        char_key,
        'hp':          c['hp'],
        'max_hp':      c['hp'],
        'energy':      c['energy'],
        'max_energy':  c['energy'],
        'effects':     {},          # effect_name → expire_time
        'normal_cd':   0.0,
        'skill_cds':   [0.0, 0.0, 0.0],
        'energy_regen_at': time.time(),
        'alive':       True,
    }

def regen_energy(state):
    now = time.time()
    dt  = now - state['energy_regen_at']
    if dt >= 0.25:
        gain = int(dt * ENERGY_REGEN)
        if gain > 0:
            state['energy'] = min(state['max_energy'], state['energy'] + gain)
            state['energy_regen_at'] = now

def expire_effects(state):
    now = time.time()
    state['effects'] = {k: v for k, v in state['effects'].items() if v > now}

def calc_damage(attacker, defender, base_dmg, is_skill=False):
    c_atk  = CHARACTERS[attacker['char']]
    c_def  = CHARACTERS[defender['char']]
    atk    = c_atk['atk']
    defense= c_def['def']

    # Áp dụng buff ATK
    if 'atk_up' in attacker['effects']:
        atk = int(atk * 1.45)

    # Áp dụng buff DEF
    if 'def_up' in defender['effects']:
        defense = int(defense * 1.35)

    # Dodge giảm 70% sát thương
    dodge_reduction = 0.3 if 'dodge' in defender['effects'] else 1.0

    raw = base_dmg + atk - defense // (2 if is_skill else 3)
    raw += random.randint(-6, 6)
    raw  = max(1, int(raw * dodge_reduction))
    return raw

def state_snapshot(room):
    def fmt(p):
        return {
            'hp':          p['hp'],
            'max_hp':      p['max_hp'],
            'energy':      p['energy'],
            'max_energy':  p['max_energy'],
            'effects':     list(p['effects'].keys()),
            'skill_cds':   [max(0, cd - time.time()) for cd in p['skill_cds']],
            'normal_cd':   max(0, p['normal_cd'] - time.time()),
        }
    st = room['state']
    return {'p1': fmt(st['p1']), 'p2': fmt(st['p2'])}

# ══════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:f>')
def serve_file(f):
    return send_from_directory('.', f)

# ══════════════════════════════════════════════
#  SOCKET EVENTS
# ══════════════════════════════════════════════
@socketio.on('connect')
def on_connect():
    emit('server_hello', {'sid': __import__('flask').request.sid,
                          'chars': {k: {
                              'name': v['name'], 'hp': v['hp'],
                              'energy': v['energy'], 'atk': v['atk'],
                              'def': v['def'], 'spd': v['spd'],
                              'skills': v['skills']
                          } for k, v in CHARACTERS.items()}})

@socketio.on('disconnect')
def on_disconnect():
    from flask import request
    sid = request.sid
    if sid not in player_rooms:
        return
    rid = player_rooms.pop(sid)
    if rid in rooms:
        rooms[rid]['players'] = [p for p in rooms[rid]['players'] if p != sid]
        socketio.emit('opponent_left', {}, room=rid)
        if not rooms[rid]['players']:
            del rooms[rid]

@socketio.on('create_room')
def on_create_room(data):
    from flask import request
    sid      = request.sid
    room_id  = (data.get('room_id') or '').strip().upper()

    # Sinh ID ngẫu nhiên nếu để trống
    if not room_id:
        room_id = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=6))

    # ID đã tồn tại và đang dùng → báo lỗi
    if room_id in rooms and rooms[room_id]['players']:
        emit('room_error', {'msg': f'Phòng "{room_id}" đã có người. Hãy chọn ID khác!'})
        return

    rooms[room_id] = {'players': [], 'chars': {}, 'started': False,
                      'state': None, 'round_start': None}

    join_room(room_id)
    rooms[room_id]['players'].append(sid)
    player_rooms[sid] = room_id
    emit('room_created', {'room_id': room_id, 'player_num': 1})


@socketio.on('join_room_by_id')
def on_join_room(data):
    from flask import request
    sid     = request.sid
    room_id = (data.get('room_id') or '').strip().upper()

    if room_id not in rooms:
        emit('room_error', {'msg': f'Phòng "{room_id}" không tồn tại!'})
        return
    room = rooms[room_id]
    if room['started']:
        emit('room_error', {'msg': 'Trận đấu đã bắt đầu rồi!'})
        return
    if len(room['players']) >= 2:
        emit('room_error', {'msg': 'Phòng đã đủ 2 người!'})
        return

    join_room(room_id)
    room['players'].append(sid)
    player_rooms[sid] = room_id
    emit('room_joined', {'room_id': room_id, 'player_num': 2})
    socketio.emit('opponent_joined', {}, room=room_id)

@socketio.on('select_char')
def on_select_char(data):
    from flask import request
    sid  = request.sid
    if sid not in player_rooms: return
    rid  = player_rooms[sid]
    room = rooms[rid]
    pnum = room['players'].index(sid) + 1
    char = data.get('char')
    if char not in CHARACTERS: return

    room['chars'][f'p{pnum}'] = char
    socketio.emit('char_picked', {'pnum': pnum, 'char': char}, room=rid)

    # Cả 2 đã chọn → bắt đầu
    if 'p1' in room['chars'] and 'p2' in room['chars']:
        room['state'] = {
            'p1': new_player_state(room['chars']['p1']),
            'p2': new_player_state(room['chars']['p2']),
        }
        room['started']     = True
        room['round_start'] = time.time()
        socketio.emit('battle_start', {
            'p1_char': room['chars']['p1'],
            'p2_char': room['chars']['p2'],
            'p1_info': CHARACTERS[room['chars']['p1']],
            'p2_info': CHARACTERS[room['chars']['p2']],
        }, room=rid)

@socketio.on('action')
def on_action(data):
    from flask import request
    sid  = request.sid
    if sid not in player_rooms: return
    rid  = player_rooms[sid]
    room = rooms[rid]
    if not room.get('started') or not room.get('state'): return

    pnum   = room['players'].index(sid) + 1
    onum   = 3 - pnum
    me     = room['state'][f'p{pnum}']
    opp    = room['state'][f'p{onum}']
    now    = time.time()

    regen_energy(me)
    regen_energy(opp)
    expire_effects(me)
    expire_effects(opp)

    result = {
        'pnum': pnum, 'action': data.get('type'),
        'dmg': 0, 'heal': 0, 'effect': None,
        'msg': '', 'crit': False, 'miss': False,
    }

    # Kiểm tra stun & silence
    if 'stun' in me['effects']:
        result['msg'] = f'P{pnum} đang bị choáng!'
        result['state'] = state_snapshot(room)
        emit('action_result', result)
        return

    atype = data.get('type')

    # ── Đánh thường ─────────────────────────────
    if atype == 'normal':
        if now < me['normal_cd']:
            result['msg'] = 'Cooldown!'; result['state'] = state_snapshot(room)
            emit('action_result', result); return
        me['normal_cd'] = now + NORMAL_ATK_CD
        crit  = random.random() < 0.15
        dmg   = calc_damage(me, opp, 0)
        if crit: dmg = int(dmg * 1.8); result['crit'] = True
        # Slow giảm SPD, không giảm dmg ở đây nhưng tăng CD
        opp['hp'] = max(0, opp['hp'] - dmg)
        result['dmg'] = dmg
        result['msg']  = f'⚔ P{pnum} tấn công {dmg} dmg!' + (' CRIT!' if crit else '')

    # ── Skill ────────────────────────────────────
    elif atype == 'skill':
        if 'silence' in me['effects']:
            result['msg'] = f'P{pnum} bị câm lặng, không dùng skill!'; result['state'] = state_snapshot(room)
            emit('action_result', result); return
        idx   = int(data.get('idx', 0))
        if idx < 0 or idx > 2: return
        sk    = CHARACTERS[me['char']]['skills'][idx]
        if now < me['skill_cds'][idx]:
            result['msg'] = f'{sk["name"]} đang hồi chiêu!'; result['state'] = state_snapshot(room)
            emit('action_result', result); return
        if me['energy'] < sk['energy_cost']:
            result['msg'] = 'Không đủ năng lượng!'; result['state'] = state_snapshot(room)
            emit('action_result', result); return

        me['energy'] -= sk['energy_cost']
        me['skill_cds'][idx] = now + sk['cooldown']
        result['skill_idx'] = idx
        result['skill_name'] = sk['name']

        # Xử lý damage
        if sk['damage'] > 0:
            dmg = calc_damage(me, opp, sk['damage'], is_skill=True)
            opp['hp'] = max(0, opp['hp'] - dmg)
            result['dmg'] = dmg

        # Xử lý effect
        eff = sk.get('effect')
        if eff:
            dur = sk.get('effect_dur', 0)
            if eff == 'burn':
                opp['effects']['burn'] = now + dur
            elif eff == 'stun':
                opp['effects']['stun'] = now + dur
            elif eff == 'slow':
                opp['effects']['slow'] = now + dur
                opp['normal_cd'] = max(opp['normal_cd'], now + 1.5)
            elif eff == 'silence':
                opp['effects']['silence'] = now + dur
            elif eff == 'def_up':
                me['effects']['def_up'] = now + dur
            elif eff == 'atk_up':
                me['effects']['atk_up'] = now + dur
            elif eff == 'dodge':
                me['effects']['dodge'] = now + dur
            elif eff == 'lifesteal':
                heal = int(result['dmg'] * 0.5)
                me['hp'] = min(me['max_hp'], me['hp'] + heal)
                result['heal'] = heal
            result['effect'] = eff

        result['msg'] = f'✨ P{pnum} dùng {sk["name"]}! ({result["dmg"]} dmg)'

    # ── Burn tick ────────────────────────────────
    if 'burn' in opp['effects']:
        opp['hp'] = max(0, opp['hp'] - BURN_DMG_TICK)
        result['burn_tick'] = BURN_DMG_TICK

    result['state'] = state_snapshot(room)

    # ── Kiểm tra thắng ───────────────────────────
    if opp['hp'] <= 0:
        result['winner'] = pnum
        result['msg']    = f'🏆 PLAYER {pnum} CHIẾN THẮNG!'
        room['started']  = False

    socketio.emit('action_result', result, room=rid)


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
if __name__ == '__main__':
    import socket as _s
    try:
        tmp = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
        tmp.connect(('8.8.8.8', 80))
        lan = tmp.getsockname()[0]
        tmp.close()
    except Exception:
        lan = '127.0.0.1'

    print('\n' + '═'*50)
    print('      ⚔  PIXEL BATTLE LAN SERVER  ⚔')
    print('═'*50)
    print(f'  LAN IP  : {lan}')
    print(f'  Game URL: http://{lan}:5000')
    print(f'  Local   : http://localhost:5000')
    print('  Chia sẻ URL trên cho người chơi cùng LAN')
    print('═'*50 + '\n')

    socketio.run(app, host='0.0.0.0', port=5000, debug=False,
                 allow_unsafe_werkzeug=True)
