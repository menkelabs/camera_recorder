"""Camera and API helpers installed into flask_gui.

These functions run inside flask_gui's namespace so tests can patch
flask_gui.DualCameraRecorder, PoseProcessor, _open_cap, and _get_recordings_dir.
"""

# ruff: noqa: F821

def _op_api_cameras_detect():
    """Try indices 0-7 and return which open. Temporarily releases cameras then re-opens with current IDs."""
    mgr = get_manager()
    if mgr is None:
        return jsonify({'error': 'Camera manager not initialized'}), 500
    if mgr.is_recording:
        return jsonify({'error': 'Stop recording before detecting cameras'}), 400
    # Release and stop capture
    mgr.running = False
    if mgr.capture_thread:
        mgr.capture_thread.join(timeout=2.0)
    mgr.capture_thread = None
    if mgr.capture_thread2:
        mgr.capture_thread2.join(timeout=2.0)
    mgr.capture_thread2 = None
    for cap in [mgr.cap1, mgr.cap2]:
        if cap:
            try:
                cap.release()
            except Exception:
                pass
    mgr.cap1 = mgr.cap2 = None
    mgr.latest_frame1 = mgr.latest_frame2 = None
    # Try each index with the platform-appropriate backend
    available = []
    for i in range(8):
        cap = _open_cap(i)
        if cap is not None:
            available.append(i)
            cap.release()
    # Re-open with current IDs (Linux: delay between opens + warmup so both streams work)
    mgr.cap1 = _open_cap(mgr.camera1_id)
    if sys.platform != 'win32':
        time.sleep(1.5)
    mgr.cap2 = _open_cap(mgr.camera2_id)
    cam1_ok = mgr.cap1.isOpened() if mgr.cap1 else False
    cam2_ok = mgr.cap2.isOpened() if mgr.cap2 else False
    if not cam1_ok and mgr.cap1:
        try:
            mgr.cap1.release()
        except Exception:
            pass
        mgr.cap1 = None
    if not cam2_ok and mgr.cap2:
        try:
            mgr.cap2.release()
        except Exception:
            pass
        mgr.cap2 = None
    mgr.cameras_available = cam1_ok and cam2_ok
    for cap in [mgr.cap1, mgr.cap2]:
        if cap and cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, mgr.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, mgr.height)
            cap.set(cv2.CAP_PROP_FPS, mgr.fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if sys.platform != 'win32':
        for _ in range(8):
            if mgr.cap1 and mgr.cap1.isOpened():
                mgr.cap1.read()
            if mgr.cap2 and mgr.cap2.isOpened():
                mgr.cap2.read()
            time.sleep(0.02)
    mgr.running = True
    mgr.capture_thread = threading.Thread(target=mgr._capture_loop_cam1, daemon=True)
    mgr.capture_thread.start()
    mgr.capture_thread2 = threading.Thread(target=mgr._capture_loop_cam2, daemon=True)
    mgr.capture_thread2.start()
    return jsonify({
        'available_indices': available,
        'camera1_id': mgr.camera1_id,
        'camera2_id': mgr.camera2_id,
        'camera1_available': cam1_ok,
        'camera2_available': cam2_ok,
    })


def _op__list_recording_pairs() -> List[Dict]:
    """Scan recordings/ dir, group by timestamp, return metadata sorted newest-first."""
    rec_dir = _get_recordings_dir()
    if not os.path.isdir(rec_dir):
        return []

    # Group files by timestamp
    groups = {}
    for fname in os.listdir(rec_dir):
        m = _RECORDING_PATTERN.match(fname)
        if not m:
            continue
        ts = m.group(1)
        if ts not in groups:
            groups[ts] = {}
        fpath = os.path.join(rec_dir, fname)
        if 'camera1' in fname:
            groups[ts]['camera1'] = fpath
        elif 'camera2' in fname:
            groups[ts]['camera2'] = fpath

    # Build result list
    pairs = []
    for ts, files in groups.items():
        cam1_path = files.get('camera1')
        cam2_path = files.get('camera2')
        cam1_size = os.path.getsize(cam1_path) if cam1_path and os.path.exists(cam1_path) else 0
        cam2_size = os.path.getsize(cam2_path) if cam2_path and os.path.exists(cam2_path) else 0

        # Parse datetime from timestamp
        try:
            dt = datetime.strptime(ts, '%Y%m%d_%H%M%S')
            date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            date_str = ts

        # Try to get video duration from camera1 file
        duration = None
        probe_path = cam1_path or cam2_path
        if probe_path:
            try:
                cap = cv2.VideoCapture(probe_path)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    if fps > 0 and frame_count > 0:
                        duration = round(frame_count / fps, 1)
                cap.release()
            except Exception:
                pass

        pairs.append({
            'timestamp': ts,
            'date': date_str,
            'camera1_file': os.path.basename(cam1_path) if cam1_path else None,
            'camera2_file': os.path.basename(cam2_path) if cam2_path else None,
            'camera1_size': cam1_size,
            'camera2_size': cam2_size,
            'total_size': cam1_size + cam2_size,
            'duration': duration,
        })

    # Sort newest first
    pairs.sort(key=lambda p: p['timestamp'], reverse=True)
    return pairs


def _op__delete_recording_pair(ts: str) -> Dict:
    """Delete both camera files for a given timestamp. Returns status dict."""
    if not _RECORDING_PATTERN.match(f'recording_{ts}_camera1.mp4'):
        return {'error': f'Invalid timestamp format: {ts}'}

    if _is_protected_timestamp(ts):
        return {'error': f'Cannot delete {ts} — currently being analyzed'}

    rec_dir = _get_recordings_dir()
    blocked = _owned_by_other_player(ts)
    if blocked:
        return {'error': blocked, 'timestamp': ts}
    deleted = []
    errors = []
    for cam in ['camera1', 'camera2']:
        fpath = os.path.join(rec_dir, f'recording_{ts}_{cam}.mp4')
        if os.path.exists(fpath):
            # Verify it's inside recordings dir (safety)
            real = os.path.realpath(fpath)
            if not real.startswith(os.path.realpath(rec_dir)):
                errors.append(f'{cam}: path outside recordings directory')
                continue
            try:
                os.remove(fpath)
                deleted.append(os.path.basename(fpath))
            except Exception as e:
                errors.append(f'{cam}: {e}')

    # Also remove analysis JSON and practice meta if present.
    # The JSON must resolve to analysis_<ts>.json inside recordings. A symlink
    # to another file is not unlinked, so a delete cannot remove that file.
    analysis_name = f'analysis_{ts}.json'
    analysis_path = os.path.join(rec_dir, analysis_name)
    if os.path.exists(analysis_path):
        expected = os.path.join(os.path.realpath(rec_dir), analysis_name)
        if os.path.realpath(analysis_path) != expected:
            errors.append('analysis: path outside recordings directory')
        else:
            try:
                os.remove(analysis_path)
                deleted.append(analysis_name)
            except Exception as e:
                errors.append(f'analysis: {e}')
    try:
        delete_recording_meta(rec_dir, ts)
    except Exception:
        pass
    deleted.extend(remove_overlay_files(rec_dir, ts))

    result = {'timestamp': ts, 'deleted': deleted}
    if errors:
        result['errors'] = errors
    return result


def _op_api_list_recordings():
    """List recording pairs for the active user (plus unclaimed by default)."""
    pairs = _list_recording_pairs()
    rec_dir = _get_recordings_dir()
    db = get_db(rec_dir)
    owners = db.ownership_map()
    users_by_id = {u['id']: u for u in db.list_users()}
    active = db.get_active_user_id()
    scope = (request.args.get('scope') or 'mine').lower()
    filtered = []
    for p in pairs:
        ts = p.get('timestamp')
        owner = owners.get(ts)
        p['owner_id'] = owner
        p['owned_by_me'] = owner == active
        p['unclaimed'] = owner is None
        p['owner_name'] = (users_by_id.get(owner) or {}).get('name') if owner else None
        if scope == 'all':
            filtered.append(p)
        elif scope == 'unclaimed':
            if owner is None:
                filtered.append(p)
        else:
            if owner is None or owner == active:
                filtered.append(p)
    pairs = attach_meta_to_pairs(rec_dir, filtered)
    ref = get_reference_timestamp(rec_dir)
    for p in pairs:
        p['is_reference'] = (p.get('timestamp') == ref)
        p['has_analysis'] = os.path.isfile(
            os.path.join(rec_dir, f"analysis_{p.get('timestamp')}.json")
        )
    total_size = sum(p['total_size'] for p in pairs)
    oldest = pairs[-1]['date'] if pairs else None
    newest = pairs[0]['date'] if pairs else None
    return jsonify({
        'recordings': pairs,
        'count': len(pairs),
        'total_size': total_size,
        'oldest': oldest,
        'newest': newest,
        'favorite_count': sum(1 for p in pairs if p.get('favorite')),
        'reference_timestamp': ref,
        'active_user': db.get_active_user(),
        'scope': scope,
    })


def _op_api_recordings_cleanup():
    """Delete the active user's (and unclaimed) recordings older than max_age_days.

    Skips other players' files, the pinned reference swing, and favorites.
    Body: {"max_age_days": 30}
    """
    data = request.get_json(silent=True) or {}
    max_age_days = data.get('max_age_days')
    if max_age_days is None:
        return jsonify({'error': 'Missing max_age_days'}), 400
    # int(True) is 1 and int(1.9) is 1. Those must not delete recordings.
    if type(max_age_days) is not int or max_age_days < 1:
        return jsonify({'error': 'max_age_days must be an integer >= 1'}), 400
    try:
        cutoff = datetime.now() - timedelta(days=max_age_days)
    except OverflowError:
        return jsonify({'error': 'max_age_days must be an integer >= 1'}), 400
    pairs = _list_recording_pairs()
    rec_dir = _get_recordings_dir()
    try:
        db = get_db(rec_dir)
        owners = db.ownership_map()
        active = db.get_active_user_id()
        favorites = set(list_favorites(rec_dir))
    except Exception as exc:
        return jsonify({'error': f'Cannot verify recording owners: {exc}'}), 500
    ref = get_reference_timestamp(rec_dir)

    results = []
    skipped = []
    for p in pairs:
        ts = p['timestamp']
        try:
            dt = datetime.strptime(ts, '%Y%m%d_%H%M%S')
        except ValueError:
            continue
        if dt >= cutoff:
            continue
        owner = owners.get(ts)
        if owner is not None and owner != active:
            skipped.append({'timestamp': ts, 'reason': 'owned'})
            continue
        if ref and ts == ref:
            skipped.append({'timestamp': ts, 'reason': 'reference'})
            continue
        if ts in favorites:
            skipped.append({'timestamp': ts, 'reason': 'favorite'})
            continue
        results.append(_delete_recording_pair(ts))

    deleted_count = sum(1 for r in results if r.get('deleted'))
    for item in results:
        if item.get('error'):
            skipped.append({
                'timestamp': item.get('timestamp'),
                'reason': 'error',
                'error': item['error'],
            })
    return jsonify({
        'results': results,
        'deleted_count': deleted_count,
        'skipped': skipped,
        'skipped_count': len(skipped),
        'cutoff_date': cutoff.strftime('%Y-%m-%d %H:%M:%S'),
    })


def _op_api_progress():
    """Aggregate swing stats into progress / trend series (SQLite first)."""
    rec_dir = _get_recordings_dir()
    try:
        db = get_db(rec_dir)
        rows = db.list_swing_stats()
        if rows:
            return jsonify(build_progress_from_stats(rows))
    except Exception as e:
        print(f"Progress DB read failed, falling back to JSON: {e}")

    # Fallback: scan analysis_*.json (pre-DB installs / empty index)
    analyses_meta = _list_saved_analyses()
    owners = {}
    active = None
    try:
        db = get_db(rec_dir)
        owners = db.ownership_map()
        active = db.get_active_user_id()
    except Exception:
        pass
    settings = load_practice_settings(rec_dir)
    loaded = []
    for item in analyses_meta:
        ts = item['timestamp']
        owner = owners.get(ts)
        if owner is not None and active is not None and owner != active:
            continue
        data = _load_analysis(ts)
        if not data:
            continue
        data.setdefault('timestamp', ts)
        data.setdefault('date', item.get('date'))
        if 'score' not in data:
            data['score'] = score_analysis(role_aware_analysis(data, settings))
        loaded.append(data)
        try:
            get_db(rec_dir).upsert_swing_stats(data)
        except Exception:
            pass
    return jsonify(build_progress_series(loaded))


def _op_api_analysis_export():
    """
    Export analysis as HTML or CSV.
    Query: ?format=html|csv  & optional timestamp=YYYYMMDD_HHMMSS
    Without timestamp, exports the current in-memory analysis.
    """
    fmt = (request.args.get('format') or 'html').lower()
    ts = request.args.get('timestamp')

    if ts:
        data = _load_analysis(ts)
        if data is None:
            return jsonify({'error': f'Analysis not found for {ts}'}), 404
    else:
        mgr = get_manager()
        if mgr is None or (mgr.analysis_camera1 is None and mgr.analysis_camera2 is None):
            return jsonify({'error': 'No analysis results to export'}), 404
        # Prefer saved JSON when available so export matches disk
        path = mgr._analysis_json_path()
        if path and os.path.exists(path):
            data = load_analysis_file(path) or {}
        else:
            data = {
                'timestamp': None,
                'camera1': mgr.analysis_camera1,
                'camera2': mgr.analysis_camera2,
            }
            if path:
                m = re.search(r'analysis_(\d{8}_\d{6})\.json', path)
                if m:
                    data['timestamp'] = m.group(1)

    settings = load_practice_settings(_get_recordings_dir())
    scored = (
        data.get('score')
        if isinstance(data.get('score'), dict)
        else score_analysis(role_aware_analysis(data, settings))
    )
    stamp = data.get('timestamp') or 'current'

    if fmt == 'csv':
        body = analysis_to_csv(data, scored)
        return Response(
            body,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=swing_report_{stamp}.csv'
            },
        )

    # default HTML
    body = analysis_to_html_report(data, scored)
    return Response(
        body,
        mimetype='text/html',
        headers={
            'Content-Disposition': f'attachment; filename=swing_report_{stamp}.html'
        },
    )


def _op_api_export_clip():
    """
    Export a camera clip as MP4.
    Body: {camera: 1|2, fps?: number, timestamp?: str}

    Prefers in-memory annotated frames when they match the requested swing;
    otherwise re-encodes the saved recording from disk.
    """
    mgr = get_manager()
    data = request.get_json(silent=True) or {}
    try:
        cam = int(data.get('camera') or 1)
    except (TypeError, ValueError):
        return _err('camera must be 1 or 2', 400)
    if cam not in (1, 2):
        return _err('camera must be 1 or 2', 400)
    raw_fps = data.get('fps', None)
    if raw_fps is None:
        fps = 30.0
    else:
        try:
            from clip_exporter import require_clip_fps
            fps = require_clip_fps(raw_fps)
        except ValueError as exc:
            return _err(str(exc), 400)

    ts = data.get('timestamp')
    if ts is not None:
        ts = str(ts).strip() or None
    if ts and not re.match(r'^\d{8}_\d{6}$', ts):
        return _err('Invalid timestamp', 400)

    live_ts = _live_analysis_timestamp(mgr)
    stamp = ts or live_ts
    memory_frames = None
    if mgr is not None and (not ts or ts == live_ts):
        memory_frames = mgr.analysis_frames_cam1 if cam == 1 else mgr.analysis_frames_cam2
        if not memory_frames:
            memory_frames = None

    out_stamp = stamp or datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = resolve_clip_output(_get_recordings_dir(), out_stamp, cam)
    try:
        if memory_frames:
            result = jpeg_frames_to_mp4(memory_frames, out_path, fps=fps)
            result['source'] = 'memory'
        elif stamp:
            rec_path = os.path.join(
                _get_recordings_dir(), f'recording_{stamp}_camera{cam}.mp4',
            )
            if not os.path.isfile(rec_path):
                return _err(f'No recording for {stamp} camera {cam}', 404)
            result = video_file_to_mp4(rec_path, out_path, fps=fps)
            result['source'] = 'saved'
        else:
            return _err(
                'No annotated frames in memory and no recording timestamp',
                400,
            )
    except ValueError as e:
        return _err(str(e), 400)
    return jsonify({'success': True, **result})


def _op_api_archive_run():
    """Archive un-archived recordings for the active user (+ unclaimed)."""
    archive_path = _get_archive_path()
    if not archive_path:
        return jsonify({'error': 'Archive path not configured'}), 400
    if not os.path.isdir(archive_path) and not os.path.isdir(os.path.dirname(archive_path)):
        return jsonify({'error': f'Archive path not accessible: {archive_path}'}), 400

    data = request.get_json(silent=True) or {}
    requested_ts = data.get('timestamps')

    manifest = _load_archive_manifest()
    pairs = _archivable_for_active_user(_list_recording_pairs())

    if requested_ts:
        pairs = [p for p in pairs if p['timestamp'] in requested_ts]
    else:
        pairs = [p for p in pairs if p['timestamp'] not in manifest]

    results = []
    for p in pairs:
        ts = p['timestamp']
        result = _archive_recording(ts, archive_path)
        if result.get('copied'):
            manifest[ts] = {
                'archived_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'files': result['copied'],
            }
        results.append(result)

    _save_archive_manifest(manifest)

    total_copied = sum(len(r.get('copied', [])) for r in results)
    return jsonify({
        'results': results,
        'archived_count': len([r for r in results if r.get('copied')]),
        'total_files_copied': total_copied,
    })


def _op_start(self):
    """Initialize cameras and start background capture thread."""
    print(f"Starting cameras: cam1={self.camera1_id}, cam2={self.camera2_id}")
    print(f"Resolution: {self.width}x{self.height} @ {self.fps}fps (120fps recording target)")

    self.cap1 = _open_cap(self.camera1_id)

    # Ubuntu/Linux: two identical USB cams need a short delay so the driver
    # can finish initializing the first device before opening the second.
    if sys.platform != 'win32':
        time.sleep(1.5)

    self.cap2 = _open_cap(self.camera2_id)

    cam1_ok = self.cap1.isOpened() if self.cap1 else False
    cam2_ok = self.cap2.isOpened() if self.cap2 else False
    self.cameras_available = cam1_ok and cam2_ok

    if not cam1_ok:
        print(f"WARNING: Camera 1 (ID: {self.camera1_id}) not available")
        if self.cap1:
            try:
                self.cap1.release()
            except Exception:
                pass
        self.cap1 = None

    if not cam2_ok:
        requested_cam2 = self.camera2_id
        if self.cap2:
            try:
                self.cap2.release()
            except Exception:
                pass
        self.cap2 = None
        # Try other indices for camera 2 (skip camera1_id). For two identical cams, try
        # requested+1 and requested-1 first (second device often at next node).
        def try_open(idx):
            return _open_cap(idx)
        order = [requested_cam2, requested_cam2 + 1, requested_cam2 - 1]
        order += [i for i in range(8) if i not in order and i != self.camera1_id]
        for idx in order:
            if idx < 0 or idx == self.camera1_id:
                continue
            cap2_try = try_open(idx)
            if cap2_try is not None:
                self.cap2 = cap2_try
                self.camera2_id = idx
                cam2_ok = True
                print(f"Camera 2 opened at index {idx} (requested {requested_cam2} was unavailable)")
                break
        if not cam2_ok and sys.platform != 'win32':
            # Linux: try by device path (helps with identical UVC cams)
            for dev in sorted([f for f in os.listdir('/dev') if f.startswith('video')], key=lambda x: int(x.replace('video', '')) if x.replace('video', '').isdigit() else 999):
                path = os.path.join('/dev', dev)
                try:
                    idx = int(dev.replace('video', ''))
                except ValueError:
                    continue
                if idx == self.camera1_id:
                    continue
                cap2_try = cv2.VideoCapture(path)
                if cap2_try.isOpened():
                    self.cap2 = cap2_try
                    self.camera2_id = idx
                    cam2_ok = True
                    print(f"Camera 2 opened at {path} (index {idx})")
                    break
                if cap2_try:
                    try:
                        cap2_try.release()
                    except Exception:
                        pass
        if not cam2_ok:
            print(f"WARNING: Camera 2 (ID: {requested_cam2}) not available; tried indices and device paths")

    self.cameras_available = cam1_ok and cam2_ok

    # Configure cameras
    for cap in [self.cap1, self.cap2]:
        if cap and cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    # Print actual camera info
    for cam_num, cap in [(1, self.cap1), (2, self.cap2)]:
        if cap and cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            f = cap.get(cv2.CAP_PROP_FPS)
            print(f"Camera {cam_num}: {w}x{h} @ {f:.1f}fps")
        else:
            print(f"Camera {cam_num}: Not available")

    # Linux: warmup reads so both cameras deliver frames (V4L2 can return False for first few reads)
    if not sys.platform == 'win32':
        for _ in range(8):
            if self.cap1 and self.cap1.isOpened():
                self.cap1.read()
            if self.cap2 and self.cap2.isOpened():
                self.cap2.read()
            time.sleep(0.02)

    # Start two capture threads (one per camera) - fixes Ubuntu/V4L2 "camera 2 opens but no frames"
    self.running = True
    self.capture_thread = threading.Thread(target=self._capture_loop_cam1, daemon=True)
    self.capture_thread.start()
    self.capture_thread2 = threading.Thread(target=self._capture_loop_cam2, daemon=True)
    self.capture_thread2.start()

    print("Camera manager started")
    self.restore_session_from_settings()


def _op__maybe_auto_detect(self, frame, cam_num: int) -> None:
    """Run swing detection on the Face-On camera only."""
    if not self.auto_detect_enabled or not self.swing_detector or self.is_recording:
        return
    if cam_num != self._face_on_camera_num():
        return
    self.auto_detect_frame_counter += 1
    if self.auto_detect_frame_counter % 4 != 0:
        return
    try:
        event = self.swing_detector.process_frame(frame)
        if event == 'start' and not self.is_recording:
            print("[AutoDetect] Swing detected — starting recording")
            self.start_recording()
        elif event == 'stop' and self.is_recording:
            print("[AutoDetect] Swing ended — stopping recording")
            self.stop_recording()
    except Exception as e:
        print(f"[AutoDetect] Error: {e}")


def _op_start_recording(self) -> Dict:
    """Start dual camera 120fps recording."""
    if self.is_recording:
        return {'error': 'Already recording'}

    checklist = self.get_pre_record_checklist()
    if not checklist['ready']:
        failed = [i['label'] for i in checklist['items'] if i.get('required') and not i['ok']]
        msg = 'Checklist failed: ' + '; '.join(failed[:3])
        self.status_message = msg
        self.status_time = time.time()
        return {'error': msg, 'checklist': checklist}

    if not self.cameras_available:
        self.status_message = "Cameras not available - cannot record"
        self.status_time = time.time()
        return {'error': 'Cameras not available'}

    if not (self.cap1 and self.cap1.isOpened() and self.cap2 and self.cap2.isOpened()):
        self.status_message = "Cameras not available - cannot record"
        self.status_time = time.time()
        return {'error': 'Camera state mismatch'}

    try:
        # Save current camera settings before releasing
        cam1_settings = {}
        cam2_settings = {}
        if self.cap1 and self.cap1.isOpened():
            for cv_prop in self.PROP_MAP.values():
                cam1_settings[cv_prop] = self.cap1.get(cv_prop)
        if self.cap2 and self.cap2.isOpened():
            for cv_prop in self.PROP_MAP.values():
                cam2_settings[cv_prop] = self.cap2.get(cv_prop)

        # Release preview cameras so the recorder can claim them
        for cap in [self.cap1, self.cap2]:
            if cap and cap.isOpened():
                try:
                    cap.release()
                except Exception:
                    pass

        # Clear frame buffers
        with self.frame_lock:
            self.latest_frame1 = None
            self.latest_frame2 = None

        # Create and start the recorder (120fps target)
        self.recorder = DualCameraRecorder(
            camera1_id=self.camera1_id,
            camera2_id=self.camera2_id,
        )
        self.recorder.output_dir = _get_recordings_dir()
        os.makedirs(self.recorder.output_dir, exist_ok=True)
        self.recorder.start_cameras(width=self.width, height=self.height, fps=self.fps)

        # Re-apply camera settings to the recorder's cameras
        for cv_prop, value in cam1_settings.items():
            try:
                self.recorder.camera1.cap.set(cv_prop, value)
            except Exception:
                pass
        for cv_prop, value in cam2_settings.items():
            try:
                self.recorder.camera2.cap.set(cv_prop, value)
            except Exception:
                pass

        # Generate output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"recording_{timestamp}"
        self.recorder.start_recording(filename)

        self.is_recording = True
        self.recording_start_time = time.time()
        self.recording_files = [
            os.path.join(self.recorder.output_dir, f"{filename}_camera1.mp4"),
            os.path.join(self.recorder.output_dir, f"{filename}_camera2.mp4"),
        ]
        if self.session_enabled:
            self.session_phase = 'recording'

        self.status_message = "Recording started"
        self.status_time = time.time()
        # Bind this swing to the active local profile immediately
        try:
            get_db(_get_recordings_dir()).claim_recording(timestamp)
        except Exception as e:
            print(f"Failed to claim recording for active user: {e}")
        print(f"Recording started: {filename} @ {self.fps}fps")
        return {'success': True, 'filename': filename}

    except Exception as e:
        self.is_recording = False
        if self.recorder:
            try:
                self.recorder.stop_cameras()
            except Exception:
                pass
            self.recorder = None
        self._reopen_cameras()
        self.status_message = f"Recording error: {e}"
        self.status_time = time.time()
        return {'error': str(e)}


def _op_stop_recording(self) -> Dict:
    """Stop recording, reopen preview cameras, trigger analysis."""
    if not self.is_recording:
        return {'error': 'Not recording'}

    if not self.recorder:
        self.is_recording = False
        return {'error': 'No active recorder'}

    try:
        self.recorder.stop_recording()
        self.recorder.stop_cameras()
        self.is_recording = False

        duration = (time.time() - self.recording_start_time) if self.recording_start_time else 0
        self.last_take = take_stats(self.recorder, duration)
        self.status_message = f"Recording stopped ({duration:.1f}s)"
        self.status_time = time.time()
        self.recording_start_time = None

        print(f"Recording stopped. Duration: {duration:.1f}s")
        if self.recording_files:
            for f in self.recording_files:
                print(f"  {f}")

        time.sleep(0.5)
        self._reopen_cameras()
        time.sleep(0.5)
        self.recorder = None

        # Auto-start analysis
        if self.recording_files and len(self.recording_files) == 2:
            if self.session_enabled:
                self.session_phase = 'analyzing'
            self.start_analysis()

        return {
            'success': True,
            'duration': duration,
            'last_take': self.last_take,
            'session_phase': self.session_phase,
            'session_enabled': self.session_enabled,
        }

    except Exception as e:
        self.is_recording = False
        if self.recorder:
            try:
                self.recorder.stop_cameras()
            except Exception:
                pass
        self.recorder = None
        self._reopen_cameras()
        self.status_message = f"Error stopping: {e}"
        self.status_time = time.time()
        return {'error': str(e)}


def _op__reopen_cameras(self):
    """Re-open cameras for preview after recording finishes."""
    if not self.cameras_available:
        return
    try:
        self.cap1 = _open_cap(self.camera1_id)
        if sys.platform != 'win32':
            time.sleep(1.5)
        self.cap2 = _open_cap(self.camera2_id)

        for cap in [self.cap1, self.cap2]:
            if cap and cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                cap.set(cv2.CAP_PROP_FPS, self.fps)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            else:
                print("WARNING: Failed to reopen a camera after recording")

        # Warmup reads on Linux
        if sys.platform != 'win32':
            for _ in range(8):
                if self.cap1 and self.cap1.isOpened():
                    self.cap1.read()
                if self.cap2 and self.cap2.isOpened():
                    self.cap2.read()
                time.sleep(0.02)
    except Exception as e:
        print(f"Error reopening cameras: {e}")
        self.cap1 = None
        self.cap2 = None


def _op_set_session_enabled(self, enabled: bool, *, persist: bool = True) -> dict:
    """Enable/disable practice session loop."""
    settings = load_practice_settings(_get_recordings_dir())
    session_prefs = settings.get('session') or {}
    if enabled:
        checklist = self.get_pre_record_checklist()
        if not checklist['ready']:
            failed = [i['label'] for i in checklist['items']
                      if i.get('required') and not i['ok']]
            return {
                'enabled': False,
                'phase': self.session_phase,
                'error': 'Checklist failed: ' + '; '.join(failed[:3]),
                'checklist': checklist,
                'count': self.session_count,
            }
        self.session_enabled = True
        self.session_phase = 'armed'
        if session_prefs.get('auto_detect', True) and not self.auto_detect_enabled:
            toggle = self.toggle_auto_detect()
            if toggle.get('error'):
                self.session_enabled = False
                self.session_phase = 'idle'
                return {
                    'enabled': False,
                    'phase': 'idle',
                    'error': toggle['error'],
                    'checklist': toggle.get('checklist'),
                    'count': self.session_count,
                }
        self.status_message = 'Session mode on — ready for next swing'
        self.status_time = time.time()
    else:
        self.session_enabled = False
        self.session_phase = 'idle'
        if self.auto_detect_enabled:
            self.toggle_auto_detect()
        self.status_message = 'Session mode off'
        self.status_time = time.time()
    if persist:
        update_practice_settings(_get_recordings_dir(), {
            'session': {**session_prefs, 'enabled': self.session_enabled}
        })
    return self.get_session_status()


def _op__analyze_videos(self):
    """Background thread: run MediaPipe pose analysis on both videos."""
    try:
        self._clear_analysis_frames()

        video1_path = self.recording_files[0]
        video2_path = self.recording_files[1]
        time.sleep(1.0)  # let video files flush

        if not os.path.exists(video1_path):
            raise FileNotFoundError(f"Not found: {video1_path}")
        if not os.path.exists(video2_path):
            raise FileNotFoundError(f"Not found: {video2_path}")

        # Get video dimensions
        cap = cv2.VideoCapture(video1_path)
        frame_width1 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if cap.isOpened() else 1280
        cap.release()
        cap = cv2.VideoCapture(video2_path)
        frame_width2 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if cap.isOpened() else 1280
        cap.release()

        # --- Camera 1 (face-on) ---
        mc = self.analysis_model_complexity
        self.analysis_progress = f"Processing Camera 1 (face-on, model={mc})..."
        processor1 = PoseProcessor(model_complexity=mc)
        landmarks1, annotated1 = processor1.process_video(video1_path)
        processor1.release()
        self.analysis_frames_cam1 = self._compress_frames(annotated1)
        del annotated1  # free raw BGR memory immediately

        calc1 = SwayCalculator()
        analysis1 = calc1.analyze_sequence(landmarks1, frame_width1)
        detected1 = sum(1 for lm in landmarks1 if lm is not None)
        analysis1['detection_rate'] = (detected1 / len(landmarks1) * 100) if landmarks1 else 0
        self.analysis_camera1 = analysis1

        # --- Camera 2 (down-the-line) ---
        self.analysis_progress = f"Processing Camera 2 (down-the-line, model={mc})..."
        processor2 = PoseProcessor(model_complexity=mc)
        landmarks2, annotated2 = processor2.process_video(video2_path)
        processor2.release()
        self.analysis_frames_cam2 = self._compress_frames(annotated2)
        del annotated2

        calc2 = SwayCalculator()
        analysis2 = calc2.analyze_sequence(landmarks2, frame_width2)
        detected2 = sum(1 for lm in landmarks2 if lm is not None)
        analysis2['detection_rate'] = (detected2 / len(landmarks2) * 100) if landmarks2 else 0
        self.analysis_camera2 = analysis2

        self.is_analyzing = False
        self.analysis_progress = ""
        elapsed = time.time() - self.analysis_start_time if self.analysis_start_time else 0
        self.status_message = f"Analysis complete ({elapsed:.1f}s)"
        self.status_time = time.time()
        print(f"Analysis complete in {elapsed:.1f}s")

        self.analysis_capture = _capture_meta(processor1, processor2)
        self._write_pose_overlays()
        # Auto-save analysis results to JSON alongside the recordings
        self._save_analysis_json()

        if self.session_enabled:
            self.session_phase = 'review'
            self.session_count += 1
            self.status_message = (
                f"Session swing #{self.session_count} ready for review "
                f"({elapsed:.1f}s analysis)"
            )

    except Exception as e:
        self.is_analyzing = False
        self.analysis_progress = ""
        self.analysis_error = str(e)
        self.status_message = f"Analysis failed: {e}"
        self.status_time = time.time()
        if self.session_enabled:
            self.session_phase = 'armed'
        print(f"Analysis error: {e}")
        import traceback
        traceback.print_exc()


def _op_reinit_cameras(self) -> Dict:
    """Release and re-open cameras with same IDs. Use after plugging in cameras."""
    if self.is_recording:
        return {'error': 'Stop recording before re-initializing cameras'}

    self.running = False
    if self.capture_thread:
        self.capture_thread.join(timeout=2.0)
    self.capture_thread = None
    if self.capture_thread2:
        self.capture_thread2.join(timeout=2.0)
    self.capture_thread2 = None

    for cap in [self.cap1, self.cap2]:
        if cap:
            try:
                cap.release()
            except Exception:
                pass
    self.cap1 = None
    self.cap2 = None
    self.cameras_available = False
    self.latest_frame1 = None
    self.latest_frame2 = None

    self.cap1 = _open_cap(self.camera1_id)
    if sys.platform != 'win32':
        time.sleep(1.5)
    self.cap2 = _open_cap(self.camera2_id)

    cam1_ok = self.cap1.isOpened() if self.cap1 else False
    cam2_ok = self.cap2.isOpened() if self.cap2 else False
    self.cameras_available = cam1_ok and cam2_ok

    if not cam1_ok:
        if self.cap1:
            try:
                self.cap1.release()
            except Exception:
                pass
        self.cap1 = None
    if not cam2_ok:
        if self.cap2:
            try:
                self.cap2.release()
            except Exception:
                pass
        self.cap2 = None
        requested_cam2 = self.camera2_id
        order = [requested_cam2, requested_cam2 + 1, requested_cam2 - 1]
        order += [i for i in range(8) if i not in order and i != self.camera1_id]
        for idx in order:
            if idx < 0 or idx == self.camera1_id:
                continue
            cap2_try = _open_cap(idx)
            if cap2_try is not None:
                self.cap2 = cap2_try
                self.camera2_id = idx
                cam2_ok = True
                break
        if not cam2_ok and sys.platform != 'win32':
            for dev in sorted([f for f in os.listdir('/dev') if f.startswith('video')], key=lambda x: int(x.replace('video', '')) if x.replace('video', '').isdigit() else 999):
                path = os.path.join('/dev', dev)
                try:
                    idx = int(dev.replace('video', ''))
                except ValueError:
                    continue
                if idx == self.camera1_id:
                    continue
                cap2_try = _open_cap(path)
                if cap2_try is not None:
                    self.cap2 = cap2_try
                    self.camera2_id = idx
                    cam2_ok = True
                    break
        self.cameras_available = cam1_ok and cam2_ok

    for cap in [self.cap1, self.cap2]:
        if cap and cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not sys.platform == 'win32':
        for _ in range(8):
            if self.cap1 and self.cap1.isOpened():
                self.cap1.read()
            if self.cap2 and self.cap2.isOpened():
                self.cap2.read()
            time.sleep(0.02)

    self.running = True
    self.capture_thread = threading.Thread(target=self._capture_loop_cam1, daemon=True)
    self.capture_thread.start()
    self.capture_thread2 = threading.Thread(target=self._capture_loop_cam2, daemon=True)
    self.capture_thread2.start()

    return {
        'camera1_available': self.cap1 is not None and self.cap1.isOpened(),
        'camera2_available': self.cap2 is not None and self.cap2.isOpened(),
        'cameras_available': self.cameras_available,
    }

