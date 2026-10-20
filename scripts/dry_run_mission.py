#!/usr/bin/env python3
import json, math, sys, time
from pymavlink import mavutil

plan_path, speed_cms = sys.argv[1], float(sys.argv[2])
items = json.load(open(plan_path))["mission"]["items"]
home = json.load(open(plan_path))["mission"]["plannedHomePosition"]

m = mavutil.mavlink_connection("udpin:127.0.0.1:14550")
m.wait_heartbeat(timeout=150)
print("connected, sys", m.target_system)


while True:
    g = m.recv_match(type="GPS_RAW_INT", blocking=True, timeout=5)
    if g and g.fix_type >= 3:
        break


PREARM = mavutil.mavlink.MAV_SYS_STATUS_PREARM_CHECK
while True:
    st = m.recv_match(type="SYS_STATUS", blocking=True, timeout=5)
    if st and st.onboard_control_sensors_health & PREARM:
        break
print("pre-arm OK")

value = None
for _ in range(10):
    m.mav.param_set_send(m.target_system, m.target_component, b"WPNAV_SPEED", speed_cms,
                         mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
    p = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=3)
    if p and p.param_id == "WPNAV_SPEED":
        value = p.param_value
        if abs(value - speed_cms) < 0.5:
            break
print("WPNAV_SPEED =", value)


wps = [(0, 16, 0, [0, 0, 0, 0, home[0], home[1], home[2]])]
for i, it in enumerate(items, 1):
    wps.append((i, it["command"], it["frame"], [0 if v is None else v for v in it["params"]]))
m.mav.mission_count_send(m.target_system, m.target_component, len(wps))
while True:
    req = m.recv_match(type=["MISSION_REQUEST", "MISSION_REQUEST_INT", "MISSION_ACK"], blocking=True, timeout=10)
    if req is None:
        sys.exit("mission upload timeout")
    if req.get_type() == "MISSION_ACK":
        print("mission ACK type", req.type); break
    seq, cmd, frame, pr = wps[req.seq]
    m.mav.mission_item_int_send(m.target_system, m.target_component, seq, frame, cmd, 0, 1,
                                pr[0], pr[1], pr[2], pr[3], int(pr[4] * 1e7), int(pr[5] * 1e7), pr[6])

m.set_mode("GUIDED")
deadline = time.time() + 300
while time.time() < deadline:
    m.arducopter_arm()
    hb = m.recv_match(type="HEARTBEAT", blocking=True, timeout=3)
    if hb and m.motors_armed():
        break
    time.sleep(3)
print("armed")
m.set_mode("AUTO")
m.mav.command_long_send(m.target_system, m.target_component, mavutil.mavlink.MAV_CMD_MISSION_START, 0, 0, 0, 0, 0, 0, 0, 0)

t0 = time.time(); max_alt = 0; max_gs = 0; last = None; gps = None; modes = []
while time.time() - t0 < 900:
    msg = m.recv_match(blocking=True, timeout=2)
    if not msg:
        continue
    t = msg.get_type()
    if t == "GLOBAL_POSITION_INT":
        last = msg; max_alt = max(max_alt, msg.relative_alt / 1000)
    elif t == "GPS_RAW_INT":
        gps = msg
    elif t == "VFR_HUD":
        max_gs = max(max_gs, msg.groundspeed)
    elif t == "STATUSTEXT":
        print("  AP:", msg.text)
    elif t == "HEARTBEAT" and msg.get_srcSystem() == m.target_system:
        if not modes or modes[-1] != m.flightmode:
            modes.append(m.flightmode)
        if not m.motors_armed() and time.time() - t0 > 20:
            break

R = 6378137.0
tgt = items[1]["params"][4:6]
dn = math.radians(last.lat / 1e7 - tgt[0]) * R
de = math.radians(last.lon / 1e7 - tgt[1]) * R * math.cos(math.radians(tgt[0]))
print(f"disarmed after {time.time()-t0:.0f}s wall; modes {modes}")
print(f"max rel alt {max_alt:.1f} m, max groundspeed {max_gs:.2f} m/s")
print(f"final EKF pos {last.lat/1e7:.7f}, {last.lon/1e7:.7f}; miss vs target {math.hypot(dn, de):.2f} m")
gn = math.radians(gps.lat / 1e7 - tgt[0]) * R
ge = math.radians(gps.lon / 1e7 - tgt[1]) * R * math.cos(math.radians(tgt[0]))
print(f"final GPS pos {gps.lat/1e7:.7f}, {gps.lon/1e7:.7f}; miss vs target {math.hypot(gn, ge):.2f} m")
