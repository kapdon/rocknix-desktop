#!/usr/bin/env python3

import json
import socket
import sys
import time


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
        chunk = sock.recv(expected - len(payload))
        if not chunk:
            raise RuntimeError("Marionette closed the connection")
        payload += chunk
    return json.loads(payload)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "support"
    default_seconds = 20 if mode == "youtube-controls" else 55
    seconds = int(sys.argv[2]) if len(sys.argv) > 2 else default_seconds
    youtube_url = (sys.argv[3] if len(sys.argv) > 3 else
                   "https://www.youtube.com/watch?v=aqz-KE-bpKQ")
    sock = socket.create_connection(("127.0.0.1", 2828), timeout=30)
    sock.settimeout(seconds + 180)
    receive(sock)
    sequence = 0
    session_open = False

    def call(name, args=None):
        nonlocal sequence
        sequence += 1
        message = json.dumps([0, sequence, name, args or {}]).encode()
        sock.sendall(str(len(message)).encode() + b":" + message)
        result = receive(sock)
        if result[2]:
            raise RuntimeError(result[2])
        return result[3]

    def navigate(url):
        target = f"{url}#codex-{time.monotonic_ns()}"
        call("WebDriver:ExecuteScript", {
            "script": """
                const url = arguments[0];
                setTimeout(() => location.assign(url), 0);
                return true;
            """,
            "args": [target],
        })
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            time.sleep(0.25)
            try:
                current = call("WebDriver:GetCurrentURL")["value"]
            except RuntimeError:
                continue
            if current == target:
                time.sleep(2)
                return
        raise RuntimeError(f"navigation did not reach {url}")

    def click_first(*selectors):
        deadline = time.monotonic() + 30
        last_error = None
        while time.monotonic() < deadline:
            for selector in selectors:
                try:
                    found = call("WebDriver:FindElement", {
                        "using": "css selector",
                        "value": selector,
                    })["value"]
                    element_id = found.get(
                        "element-6066-11e4-a52e-4f735466cecf",
                        found.get("ELEMENT"),
                    )
                    if not element_id:
                        continue
                    call("WebDriver:ElementClick", {"id": element_id})
                    return
                except RuntimeError as error:
                    last_error = error
            time.sleep(0.25)
        raise RuntimeError(
            f"could not click any of {selectors}: {last_error}"
        )

    def prepare_youtube_muted():
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            state = call("WebDriver:ExecuteScript", {
                "script": """
                    const video = document.querySelector('video');
                    const player = document.getElementById('movie_player');
                    if (!video || !player ||
                        typeof player.mute !== 'function') {
                      return null;
                    }
                    video.muted = true;
                    player.mute();
                    return {paused: video.paused,
                      readyState: video.readyState};
                """,
                "args": [],
            })["value"]
            if state:
                return state
            time.sleep(0.25)
        raise RuntimeError("YouTube player did not become ready")

    try:
        call("WebDriver:NewSession", {"capabilities": {"alwaysMatch": {
            "pageLoadStrategy": "none"
        }}})
        session_open = True
    except BaseException:
        sock.close()
        raise
    call("WebDriver:SetTimeouts", {
        "script": (seconds + 150) * 1000,
        "pageLoad": 90_000,
    })
    try:
        if mode == "console":
            call("Marionette:SetContext", {"value": "chrome"})
            result = call("WebDriver:ExecuteScript", {
                "script": """
                    return Services.console.getMessageArray().slice(-1000)
                      .map(message => ({
                        message: message.message || message.errorMessage ||
                          String(message),
                        sourceName: message.sourceName || null,
                        category: message.category || null,
                        logLevel: message.logLevel || null,
                        timeStamp: message.timeStamp || null
                      })).filter(item =>
                        /youtube|googlevideo|jnn|botguard|attest|integrity|potoken|po.token|error|fail/i
                          .test(`${item.message} ${item.sourceName} ${item.category}`)
                      );
                """,
                "args": [],
            })
        elif mode == "youtube-state":
            result = call("WebDriver:ExecuteScript", {
                "script": """
                    const player = document.getElementById('movie_player');
                    const video = document.querySelector('video');
                    const allResources = performance.getEntriesByType(
                      'resource');
                    const resourceHosts = {};
                    for (const entry of allResources) {
                      try {
                        const host = new URL(entry.name).hostname;
                        resourceHosts[host] = (resourceHosts[host] || 0) + 1;
                      } catch (_) {}
                    }
                    const protectedResources = allResources.filter(entry =>
                      /jnn|attest|botguard|integrity|challenge/i.test(
                        entry.name)).map(entry => {
                          const url = new URL(entry.name);
                          return {
                            host: url.hostname,
                            path: url.pathname,
                            duration: entry.duration,
                            transferSize: entry.transferSize,
                            encodedBodySize: entry.encodedBodySize
                          };
                        });
                    const experimentFlags = Object.fromEntries(
                      Object.entries(window.ytcfg?.data_?.EXPERIMENT_FLAGS || {})
                        .filter(([key]) =>
                          /sabr|ump|potoken|po_token|attest|botguard|integrity/i
                            .test(key))
                    );
                    const resources = allResources.slice(-80).map(entry => {
                        try {
                          const url = new URL(entry.name);
                          return {
                            host: url.hostname,
                            path: url.pathname,
                            initiatorType: entry.initiatorType,
                            duration: entry.duration,
                            transferSize: entry.transferSize,
                            encodedBodySize: entry.encodedBodySize
                          };
                        } catch (_) {
                          return null;
                        }
                      }).filter(Boolean);
                    const safeCall = (name) => {
                      try {
                        return player && typeof player[name] === 'function' ?
                          player[name]() : null;
                      } catch (error) {
                        return {error: String(error)};
                      }
                    };
                    return {
                      title: document.title,
                      url: location.href,
                      webdriver: navigator.webdriver,
                      body: document.body.innerText.slice(0, 2500),
                      playerClass: player ? player.className : null,
                      playerState: safeCall('getPlayerState'),
                      debugText: safeCall('getDebugText'),
                      videoData: safeCall('getVideoData'),
                      videoStats: safeCall('getVideoStats'),
                      playerResponse: safeCall('getPlayerResponse'),
                      errorScreen: document.querySelector(
                        '.ytp-error, .ytp-error-content-wrap')?.innerText || null,
                      video: video ? {
                        currentTime: video.currentTime,
                        duration: video.duration,
                        paused: video.paused,
                        readyState: video.readyState,
                        networkState: video.networkState,
                        error: video.error ? {
                          code: video.error.code,
                          message: video.error.message
                        } : null,
                        quality: video.getVideoPlaybackQuality()
                      } : null,
                      resourceHosts,
                      protectedResources,
                      experimentFlags,
                      resources
                    };
                """,
                "args": [],
            })
        elif mode == "support":
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
            navigate("file:///storage/Desktop/rp6-sway-firefox-test.html")
            result = call("WebDriver:ExecuteAsyncScript", {
                "script": """
                    const done = arguments[arguments.length - 1];
                    const seconds = arguments[0];
                    const started = Date.now();
                    const timer = setInterval(() => {
                      const video = document.querySelector('video');
                      if (!video || video.readyState < 1) {
                        if (Date.now() - started > 30000) {
                          clearInterval(timer);
                          done({error: 'video element did not become ready'});
                        }
                        return;
                      }
                      clearInterval(timer);
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
                    }, 100);
                """,
                "args": [seconds],
            })
        elif mode == "youtube":
            navigate(youtube_url)
            youtube_state = prepare_youtube_muted()
            if youtube_state["paused"]:
                click_first(
                    "button.ytp-large-play-button",
                    "button.ytp-play-button",
                )
            result = call("WebDriver:ExecuteAsyncScript", {
                "script": """
                    const done = arguments[arguments.length - 1];
                    const seconds = arguments[0];
                    const targetUrl = new URL(arguments[1]);
                    const expectedVideoId = targetUrl.searchParams.get('v') ||
                      targetUrl.pathname.split('/').filter(Boolean).pop();
                    const waitStarted = Date.now();
                    const timer = setInterval(async () => {
                      if (Date.now() - waitStarted > 120000) {
                        clearInterval(timer);
                        done({error: 'target video readiness timed out',
                          title: document.title});
                        return;
                      }
                      const video = document.querySelector('video');
                      const player = document.getElementById('movie_player');
                      if (player?.classList.contains('ad-showing')) {
                        document.querySelector(
                          '.ytp-skip-ad-button, ' +
                          '.ytp-ad-skip-button-modern, ' +
                          '.ytp-ad-skip-button'
                        )?.click();
                        return;
                      }
                      const videoData = player &&
                        typeof player.getVideoData === 'function' ?
                        player.getVideoData() : null;
                      if (!video || video.readyState < 1 || !player ||
                          typeof player.playVideo !== 'function' ||
                          videoData?.video_id !== expectedVideoId) {
                        if (Date.now() - waitStarted > 120000) {
                          clearInterval(timer);
                          done({error: 'target video did not become ready',
                            title: document.title,
                            body: document.body.innerText.slice(0, 2000)});
                        }
                        return;
                      }
                      clearInterval(timer);
                      // Let the trusted click start the settled player before
                      // recording playback quality.
                      setTimeout(async () => {
                        video.muted = true;
                        player.mute();
                        if (video.paused) {
                          player.playVideo();
                          try {
                            await video.play();
                          } catch (error) {
                            done({playError: String(error),
                              title: document.title});
                            return;
                          }
                        }
                        const started = Date.now();
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
                      }, 1000);
                    }, 250);
                """,
                "args": [seconds, youtube_url],
            })
        elif mode == "youtube-controls":
            navigate(youtube_url)
            click_first(
                "button.ytp-large-play-button",
                "button.ytp-play-button",
            )
            result = call("WebDriver:ExecuteAsyncScript", {
                "script": """
                    const done = arguments[arguments.length - 1];
                    const playSeconds = arguments[0];
                    const targetUrl = new URL(arguments[1]);
                    const expectedVideoId = targetUrl.searchParams.get('v') ||
                      targetUrl.pathname.split('/').filter(Boolean).pop();
                    let started = Date.now();
                    const sleep = ms => new Promise(resolve =>
                      setTimeout(resolve, ms));
                    const snapshot = (video, player) => ({
                      wallSeconds: (Date.now() - started) / 1000,
                      currentTime: video.currentTime,
                      paused: video.paused,
                      readyState: video.readyState,
                      playerState: player.getPlayerState(),
                      muted: video.muted,
                      volume: video.volume,
                      error: video.error ? {
                        code: video.error.code,
                        message: video.error.message
                      } : null,
                      quality: video.getVideoPlaybackQuality()
                    });
                    const waitForVideo = async () => {
                      while (Date.now() - started < 60000) {
                        const video = document.querySelector('video');
                        const player = document.getElementById('movie_player');
                        if (player?.classList.contains('ad-showing')) {
                          document.querySelector(
                            '.ytp-skip-ad-button, ' +
                            '.ytp-ad-skip-button-modern, ' +
                            '.ytp-ad-skip-button'
                          )?.click();
                          await sleep(250);
                          continue;
                        }
                        const videoData = player &&
                          typeof player.getVideoData === 'function' ?
                          player.getVideoData() : null;
                        if (video && video.readyState >= 1 && player &&
                            typeof player.playVideo === 'function' &&
                            videoData?.video_id === expectedVideoId) {
                          return {video, player};
                        }
                        await sleep(250);
                      }
                      throw new Error('video element did not become ready');
                    };
                    (async () => {
                      try {
                        const {video, player} = await waitForVideo();
                        await sleep(1000);
                        started = Date.now();
                        video.muted = false;
                        video.volume = 0.2;
                        player.unMute();
                        player.setVolume(20);
                        if (video.paused) {
                          player.playVideo();
                          await video.play();
                        }
                        const initial = snapshot(video, player);
                        await sleep(playSeconds * 1000);
                        const beforePause = snapshot(video, player);
                        player.pauseVideo();
                        video.pause();
                        await sleep(3000);
                        const afterPause = snapshot(video, player);
                        player.playVideo();
                        await video.play();
                        await sleep(10000);
                        const afterResume = snapshot(video, player);
                        const seekTarget = Math.min(video.duration - 30,
                          video.currentTime + 15);
                        player.seekTo(seekTarget, true);
                        player.playVideo();
                        const seekDeadline = Date.now() + 15000;
                        while (Date.now() < seekDeadline &&
                               Math.abs(video.currentTime - seekTarget) > 3) {
                          await sleep(250);
                        }
                        await sleep(5000);
                        const afterSeek = snapshot(video, player);
                        done({
                          title: document.title,
                          url: location.href,
                          initial,
                          beforePause,
                          afterPause,
                          afterResume,
                          seekTarget,
                          afterSeek,
                          pauseAdvance: afterPause.currentTime -
                            beforePause.currentTime,
                          resumeAdvance: afterResume.currentTime -
                            afterPause.currentTime,
                          seekError: Math.abs(afterSeek.currentTime -
                            (seekTarget + 5)),
                          decodedDelta:
                            afterSeek.quality.totalVideoFrames -
                            initial.quality.totalVideoFrames,
                          droppedDelta:
                            afterSeek.quality.droppedVideoFrames -
                            initial.quality.droppedVideoFrames,
                          body: document.body.innerText.slice(0, 2000)
                        });
                      } catch (error) {
                        done({error: String(error), title: document.title,
                          body: document.body.innerText.slice(0, 2000)});
                      }
                    })();
                """,
                "args": [seconds, youtube_url],
            })
        else:
            raise RuntimeError(f"unknown mode: {mode}")
        print(json.dumps(result, sort_keys=True))
    finally:
        exception_in_flight = sys.exc_info()[0] is not None
        try:
            if session_open:
                call("WebDriver:DeleteSession")
        except (OSError, RuntimeError):
            if not exception_in_flight:
                raise
        finally:
            sock.close()


if __name__ == "__main__":
    main()
