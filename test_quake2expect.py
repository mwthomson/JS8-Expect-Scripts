from quake2expect import dist_bearing, fmt, grid2latlon

lat, lon = grid2latlon("DN43AP")
assert abs(lat - 43.646) < 0.01 and abs(lon - -111.958) < 0.01, (lat, lon)
assert grid2latlon("DN43") == (43.5, -111)

# Idaho Falls -> Salt Lake City is ~190 mi, roughly south
mi, brg = dist_bearing(43.49, -112.04, 40.76, -111.89)
assert 185 < mi < 195 and 170 < brg < 190, (mi, brg)

assert fmt([], lat, lon, 24, 2.5, 100) == "QUAKE 24H NONE M2.5+ 100MI"
q = {"geometry": {"coordinates": [-111.5, 44.0, 5]},
     "properties": {"mag": 3.14, "time": 0}}
out = fmt([q, q], lat, lon, 24, 2.5, 100)
assert out.startswith("QUAKE 24H 2 MAX M3.1 ") and " NE " in out, out
assert len(out) < 40, out
print("ok")
