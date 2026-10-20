#!/usr/bin/env python3
import csv, json, math, sys
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pymavlink import mavutil

CSV_PATH, TLOG_PATH, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
H_SET, V_SET = 40.0, 5.0
TARGET = (-35.3624356, 149.1641926)
R = 6378137.0


def dist_m(a, b):
    dn = math.radians(b[0] - a[0]) * R
    de = math.radians(b[1] - a[1]) * R * math.cos(math.radians(a[0]))
    return math.hypot(dn, de)


def num(v):
    try:
        return float(v)
    except ValueError:
        return float("nan")


rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
ts = [datetime.strptime(r["Timestamp"], "%Y-%m-%d %H:%M:%S.%f") for r in rows]
alt = [num(r["altitudeRelative"]) for r in rows]
gs = [num(r["groundSpeed"]) for r in rows]
air = [num(r["airSpeed"]) for r in rows]
roll = [num(r["roll"]) for r in rows]
mi = [int(num(r["missionItemIndex"])) for r in rows]
lat = [num(r["gps.lat"]) for r in rows]
lon = [num(r["gps.lon"]) for r in rows]

i_to = next(i for i, a in enumerate(alt) if a > 0.2)
i_land = next(i for i in range(i_to + 5, len(alt)) if alt[i] <= 0.05)
t0 = ts[i_to]
t = [(x - t0).total_seconds() for x in ts]

i_cruise = next(i for i in range(i_to, i_land) if mi[i] == 2)
i_desc = next(i for i in range(i_cruise, i_land) if mi[i] == 3)
phases = [(t[i_to], t[i_cruise], "Зліт", "#4C72B0"),
          (t[i_cruise], t[i_desc], "Горизонтальний політ", "#55A868"),
          (t[i_desc], t[i_land], "Посадка", "#C44E52")]

cruise_gs = [g for i, g in enumerate(gs) if i_cruise <= i < i_desc and g > 4.5]


mlog = mavutil.mavlink_connection(TLOG_PATH, dialect="ardupilotmega")
modes, arm_states = [], []
first_arm_ms = disarm_ms = None
gpi_first = gpi_last = None
max_roll_tlog = 0.0
while True:
    m = mlog.recv_match(type=["HEARTBEAT", "GLOBAL_POSITION_INT", "ATTITUDE"])
    if m is None:
        break
    if m.get_type() == "HEARTBEAT":
        if m.get_srcSystem() != 1 or m.type == mavutil.mavlink.MAV_TYPE_GCS:
            continue
        mode = mavutil.mode_string_v10(m)
        armed = bool(m.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        if not modes or modes[-1] != mode:
            modes.append(mode)
        if not arm_states or arm_states[-1] != armed:
            arm_states.append(armed)
    elif m.get_type() == "GLOBAL_POSITION_INT":
        if m.relative_alt > 200 and first_arm_ms is None:
            first_arm_ms = m.time_boot_ms
        if first_arm_ms and m.relative_alt > 200:
            disarm_ms = m.time_boot_ms
        if gpi_first is None:
            gpi_first = m
        gpi_last = m
    elif m.get_type() == "ATTITUDE" and first_arm_ms:
        max_roll_tlog = max(max_roll_tlog, abs(math.degrees(m.roll)))

sim_flight_s = (disarm_ms - first_arm_ms) / 1000 if first_arm_ms and disarm_ms else float("nan")
wall_flight_s = t[i_land]

start = (lat[0], lon[0])
end = (lat[-1], lon[-1])
res = {
    "takeoff_time": t0.strftime("%H:%M:%S"),
    "max_alt_m": round(max(alt), 1),
    "max_groundspeed_ms": round(max(gs), 2),
    "max_airspeed_ms": round(max(air), 2),
    "cruise_groundspeed_mean_ms": round(sum(cruise_gs) / len(cruise_gs), 2),
    "flight_time_wall_s": round(wall_flight_s),
    "flight_time_csv_field": rows[i_land]["flightTime"],
    "flight_time_sim_s": round(sim_flight_s, 1),
    "start_coord": [round(start[0], 7), round(start[1], 7)],
    "end_coord": [round(end[0], 7), round(end[1], 7)],
    "max_roll_deg_csv": round(max(abs(r) for r in roll), 1),
    "max_roll_deg_tlog": round(max_roll_tlog, 2),
    "modes": modes,
    "arm_sequence": ["ARMED" if a else "DISARMED" for a in arm_states],
    "target": list(TARGET),
    "miss_to_target_m": round(dist_m(TARGET, end), 2),
    "start_to_target_m": round(dist_m(start, TARGET), 1),
    "flight_distance_m": rows[i_land]["flightDistance"],
    "alt_error_m": round(max(alt) - H_SET, 2),
    "speed_error_ms": round(max(gs) - V_SET, 2),
    "phase_s": {p[2]: [round(p[0]), round(p[1])] for p in phases},
}
json.dump(res, open(f"{OUT}/results.json", "w"), ensure_ascii=False, indent=2)
print(json.dumps(res, ensure_ascii=False, indent=2))


plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
end_t = t[i_land] + 20
for key, series, ylabel, title, ref in [
    ("altitude", alt, "Відносна висота, м", "Висота від часу", H_SET),
    ("airspeed", air, "Повітряна швидкість, м/с", "Повітряна швидкість від часу", V_SET),
    ("groundspeed", gs, "Наземна швидкість, м/с", "Наземна швидкість від часу", V_SET),
]:
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=150)
    for a, b, name, color in phases:
        ax.axvspan(a, b, color=color, alpha=0.12, lw=0)
        ax.text((a + b) / 2, 1.02, name, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=10, color=color)
    sel = [i for i in range(len(t)) if -10 <= t[i] <= end_t]
    ax.plot([t[i] for i in sel], [series[i] for i in sel], color="#222222", lw=1.8)
    ax.axhline(ref, ls="--", lw=1, color="#888888")
    ax.text(end_t, ref, f" задано {ref:g}", va="bottom", ha="right", fontsize=9, color="#666666")
    ax.set_xlim(-10, end_t)
    ax.set_xlabel("Час від зльоту, с (за записами CSV)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, pad=22)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{OUT}/{key}.png")
    plt.close(fig)
print("plots saved")
