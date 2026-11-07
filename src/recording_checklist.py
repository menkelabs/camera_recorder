"""Pre-record checklist, including disk free space and USB topology."""

from __future__ import annotations

import os
import shutil

import cv2

from practice_settings import camera_labels, load_practice_settings
from usb_health import (
    detect_shared_usb_bus,
    detect_windows_usb_controllers,
    frame_starvation_warning,
)

MIN_FREE_BYTES = 512 * 1024 * 1024


def build_pre_record_checklist(mgr, recordings_dir: str) -> dict:
    items = []
    items.extend(_camera_items(mgr))
    items.extend(_frame_items(mgr))
    items.append(_resolution_item(mgr))
    items.append(_writable_item(recordings_dir))
    items.append(_free_space_item(recordings_dir))
    items.append(_idle_item(mgr))
    items.append(_linux_usb_item(mgr))
    items.append(_windows_usb_item())

    ready = all(item['ok'] for item in items if item.get('required'))
    settings = load_practice_settings(recordings_dir)
    usb_item = next(item for item in items if item['id'] == 'usb')
    win_item = next(item for item in items if item['id'] == 'usb_controller')
    warning = None
    if not usb_item['ok']:
        warning = usb_item['detail']
    elif not win_item['ok']:
        warning = win_item['detail']
    return {
        'ready': ready,
        'items': items,
        'camera1_id': mgr.camera1_id,
        'camera2_id': mgr.camera2_id,
        'camera_labels': camera_labels(settings),
        'width': mgr.width,
        'height': mgr.height,
        'fps': mgr.fps,
        'usb_warning': warning,
    }


def _camera_items(mgr) -> list:
    cam1_ok = bool(mgr.cap1 and mgr.cap1.isOpened())
    cam2_ok = bool(mgr.cap2 and mgr.cap2.isOpened())
    return [
        {
            'id': 'camera1',
            'label': f'Camera 1 (index {mgr.camera1_id}) open',
            'ok': cam1_ok,
            'detail': 'OK' if cam1_ok else 'Not available — check Detect / USB',
            'required': True,
        },
        {
            'id': 'camera2',
            'label': f'Camera 2 (index {mgr.camera2_id}) open',
            'ok': cam2_ok,
            'detail': 'OK' if cam2_ok else 'Not available — try another index or USB port',
            'required': True,
        },
    ]


def _frame_items(mgr) -> list:
    with mgr.frame_lock:
        has_cam1 = mgr.latest_frame1 is not None
        has_cam2 = mgr.latest_frame2 is not None
    return [
        {
            'id': 'frames1',
            'label': 'Camera 1 delivering frames',
            'ok': has_cam1,
            'detail': 'Receiving preview frames' if has_cam1 else 'No recent frames',
            'required': True,
        },
        {
            'id': 'frames2',
            'label': 'Camera 2 delivering frames',
            'ok': has_cam2,
            'detail': (
                'Receiving preview frames'
                if has_cam2
                else 'No recent frames — often a USB bandwidth issue'
            ),
            'required': True,
        },
    ]


def _resolution_item(mgr) -> dict:
    cam1_ok = bool(mgr.cap1 and mgr.cap1.isOpened())
    res_ok = True
    detail = f'Target {mgr.width}x{mgr.height} @ {mgr.fps}fps'
    if cam1_ok:
        width = int(mgr.cap1.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(mgr.cap1.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if width and height:
            res_ok = width >= mgr.width * 0.9 and height >= mgr.height * 0.9
            detail = f'Cam1 reports {width}x{height}; target {mgr.width}x{mgr.height}'
    return {
        'id': 'resolution',
        'label': 'Resolution near target',
        'ok': res_ok,
        'detail': detail,
        'required': False,
    }


def _writable_item(recordings_dir: str) -> dict:
    writable = os.path.isdir(recordings_dir) and os.access(recordings_dir, os.W_OK)
    if not os.path.isdir(recordings_dir):
        try:
            os.makedirs(recordings_dir, exist_ok=True)
            writable = os.access(recordings_dir, os.W_OK)
        except OSError:
            writable = False
    return {
        'id': 'disk',
        'label': 'Recordings folder writable',
        'ok': writable,
        'detail': recordings_dir if writable else f'Cannot write to {recordings_dir}',
        'required': True,
    }


def _free_space_item(recordings_dir: str) -> dict:
    free = _free_bytes(recordings_dir)
    ok = free >= MIN_FREE_BYTES
    gib = free / (1024 ** 3)
    need = MIN_FREE_BYTES / (1024 ** 3)
    return {
        'id': 'disk_free',
        'label': 'Recordings disk has free space',
        'ok': ok,
        'detail': f'{gib:.2f} GB free — need at least {need:.2f} GB',
        'required': True,
    }


def _free_bytes(recordings_dir: str) -> int:
    try:
        return int(shutil.disk_usage(recordings_dir).free)
    except OSError:
        return 0


def _idle_item(mgr) -> dict:
    idle = not mgr.is_recording
    return {
        'id': 'not_recording',
        'label': 'Not already recording',
        'ok': idle,
        'detail': 'Idle' if idle else 'Stop the current recording first',
        'required': True,
    }


def _linux_usb_item(mgr) -> dict:
    with mgr.frame_lock:
        has_cam1 = mgr.latest_frame1 is not None
        has_cam2 = mgr.latest_frame2 is not None
    usb = detect_shared_usb_bus(mgr.camera1_id, mgr.camera2_id)
    starve = frame_starvation_warning(has_cam1, has_cam2)
    ok = True
    detail = 'Cameras on separate USB paths'
    if usb.get('shared_bus') is True:
        ok = False
        detail = usb.get('warning') or 'Shared USB bus detected'
    elif starve:
        ok = False
        detail = starve
    elif usb.get('warning') and usb.get('shared_bus') is None:
        detail = usb['warning']
    elif not usb.get('platform_supported'):
        detail = 'USB topology check is Linux-only; watch for dropped Cam2 frames'
    return {
        'id': 'usb',
        'label': 'USB bandwidth',
        'ok': ok,
        'detail': detail,
        'required': False,
        'usb': usb,
    }


def _windows_usb_item() -> dict:
    windows = detect_windows_usb_controllers()
    shared = windows.get('shared_controller') is True
    if shared:
        detail = windows.get('warning') or 'Shared USB controller'
    elif windows.get('shared_controller') is False:
        detail = 'Cameras are on different USB controllers'
    elif not windows.get('platform_supported'):
        detail = 'Windows USB controller check runs on Windows'
    elif windows.get('checked'):
        detail = 'Could not map cameras to USB controllers'
    else:
        detail = 'Windows USB controller check runs on Windows'
    return {
        'id': 'usb_controller',
        'label': 'USB controller',
        'ok': not shared,
        'detail': detail,
        'required': False,
        'windows_usb': windows,
    }
