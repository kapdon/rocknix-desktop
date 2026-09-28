#!/usr/bin/env python3

import json
import socket
import sys


def receive(sock):
    length = b""
    while not length.endswith(b":"):
        chunk = sock.recv(1)
        if not chunk:
            raise RuntimeError("Marionette closed the connection")
        length += chunk
    payload = b""
    expected = int(length[:-1])
    while len(payload) < expected:
        payload += sock.recv(expected - len(payload))
    return json.loads(payload)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "support"
    seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 55
    sock = socket.create_connection(("127.0.0.1", 2828), timeout=30)
    sock.settimeout(seconds + 120)
    receive(sock)
    sequence = 0

    def call(name, args=None):
        nonlocal sequence
        sequence += 1
        message = json.dumps([0, sequence, name, args or {}]).encode()
        sock.sendall(str(len(message)).encode() + b":" + message)
        result = receive(sock)
        if result[2]:
            raise RuntimeError(result[2])
        return result[3]

    call("WebDriver:NewSession", {"capabilities": {"alwaysMatch": {}}})
    call("WebDriver:SetTimeouts", {
        "script": (seconds + 90) * 1000,
        "pageLoad": 90_000,
    })
    try:
        if mode == "support":
            call("Marionette:SetContext", {"value": "chrome"})
            result = call("WebDriver:ExecuteAsyncScript", {
                "script": """
                    const done = arguments[arguments.length - 1];
                    ChromeUtils.importESModule(
                      'resource://gre/modules/Troubleshoot.sys.mjs'
                    ).Troubleshoot.snapshot().then(snapshot => done({
                      graphics: snapshot.graphics,
                      media: snapshot.media,
                      sandbox: snapshot.sandbox
                    }));
                """,
                "args": [],
            })
        elif mode == "local":
            call("WebDriver:Navigate", {
                "url": "file:///storage/Desktop/rp6-sway-firefox-test.html"
            })
            result = call("WebDriver:ExecuteAsyncScript", {
                "script": """
                    const done = arguments[arguments.length - 1];
                    const seconds = arguments[0];
                    const video = document.querySelector('video');
                    video.muted = true;
                    video.play().then(() => setTimeout(() => done({
                      currentTime: video.currentTime,
                      duration: video.duration,
                      paused: video.paused,
                      ended: video.ended,
                      readyState: video.readyState,
                      error: video.error,
                      width: video.videoWidth,
                      height: video.videoHeight,
                      quality: video.getVideoPlaybackQuality(),
                      webgl: document.querySelector('pre').textContent
                    }), seconds * 1000)).catch(error => done({
                      playError: String(error)
                    }));
                """,
                "args": [seconds],
            })
        elif mode == "youtube":
            call("WebDriver:Navigate", {
                "url": "https://www.youtube.com/watch?v=aqz-KE-bpKQ"
            })
            result = call("WebDriver:ExecuteAsyncScript", {
                "script": """
                    const done = arguments[arguments.length - 1];
                    const seconds = arguments[0];
                    const started = Date.now();
                    const timer = setInterval(async () => {
                      const video = document.querySelector('video');
                      const player = document.getElementById('movie_player');
                      if (!video || video.readyState < 1 || !player ||
                          typeof player.playVideo !== 'function') {
                        if (Date.now() - started > 60000) {
                          clearInterval(timer);
                          done({error: 'video element did not become ready',
                            title: document.title,
                            body: document.body.innerText.slice(0, 2000)});
                        }
                        return;
                      }
                      clearInterval(timer);
                      // Let YouTube finish replacing its initial media state
                      // before starting through both its API and the element.
                      setTimeout(async () => {
                        video.muted = true;
                        player.mute();
                        player.playVideo();
                        try {
                          await video.play();
                        } catch (error) {
                          done({playError: String(error),
                            title: document.title});
                          return;
                        }
                        const initial = video.getVideoPlaybackQuality();
                        const initialTime = video.currentTime;
                        const samples = [];
                        const monitor = setInterval(() => samples.push({
                          wallSeconds: Math.round((Date.now() - started) / 1000),
                          currentTime: video.currentTime,
                          paused: video.paused,
                          readyState: video.readyState,
                          playerState: player.getPlayerState(),
                          totalVideoFrames:
                            video.getVideoPlaybackQuality().totalVideoFrames
                        }), 10000);
                        setTimeout(() => {
                          clearInterval(monitor);
                          const quality = video.getVideoPlaybackQuality();
                          done({
                            title: document.title,
                            url: location.href,
                            initialTime,
                            currentTime: video.currentTime,
                            duration: video.duration,
                            paused: video.paused,
                            ended: video.ended,
                            readyState: video.readyState,
                            networkState: video.networkState,
                            playerState: player.getPlayerState(),
                            error: video.error,
                            width: video.videoWidth,
                            height: video.videoHeight,
                            quality,
                            decodedDelta: quality.totalVideoFrames -
                              initial.totalVideoFrames,
                            droppedDelta: quality.droppedVideoFrames -
                              initial.droppedVideoFrames,
                            bufferedEnd: video.buffered.length ?
                              video.buffered.end(video.buffered.length - 1) : 0,
                            samples,
                            body: document.body.innerText.slice(0, 2000)
                          });
                        }, seconds * 1000);
                      }, 5000);
                    }, 250);
                """,
                "args": [seconds],
            })
        else:
            raise RuntimeError(f"unknown mode: {mode}")
        print(json.dumps(result, sort_keys=True))
    finally:
        call("WebDriver:DeleteSession")


if __name__ == "__main__":
    main()
