# pod_perception

**Owner:** Person A (Hrushikesh) · **Must never import:** pymavlink, control logic
(`pod_mavlink`, `pod_guidance`, `pod_state`) `[PRD 2.3]`.

GStreamer pipeline construction and the appsink callback. Pixel work stays in C,
outside the GIL; Python touches metadata only.

```
libcamerasrc ! videoconvert ! hailonet ! hailofilter ! hailotracker ! tee
  tee. ! queue ! hailooverlay ! videoscale ! x264enc ! rtspserver   (sacrificial)
  tee. ! queue ! appsink                                            (control)
```

⚠ The appsink is **`drop=true max-buffers=1`** `[PRD 5.2]`. Frames are dropped, never
queued: *"a stale frame in a closed loop is worse than no frame."*

⚠ The video branch is **sacrificial** `[PRD 4.5]`: cap at 30 fps, downscale before
encoding, `ultrafast`/`zerolatency`, and verify it starves before the control path.
The Pi 5 has no hardware H.264 encoder.

**Status:** pipeline shape is data (`pipeline.py`), reviewable and testable off
hardware. Construction is M1 and hardware-gated. Open: OD-03 (dual-camera split),
OD-04 (letterbox vs foveated crop), OD-05 (ByteTrack at 60 fps), NMS location.

**Single writer:** the appsink callback is the only writer of `TrackFrame`.
