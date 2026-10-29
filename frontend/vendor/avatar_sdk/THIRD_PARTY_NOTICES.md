# Third-party notices for `avatar_sdk`

These notices apply to the vendored files in this directory, not to the project code covered by the repository-root `LICENSE`.

## xrtc.js / iflytek

`xrtc-player-BJTnVhG9.js` contains this upstream header:

```text
xrtc.js v5.2024.5.0_00
(c) 2020-2024
Released under the MIT License in iflytek.
```

The version and MIT statement above come directly from that header. `LICENSE-xrtc.txt` preserves the header and includes the full MIT permission and warranty notices. No copyright holder has been added beyond the attribution present in the bundle.

The original iflytek SDK download URL and its accompanying license file were not available in this repository and could not be verified from the vendored files. The headers in `index-OS7Lza_r.js`, `index.js`, and `index.d.ts` do not establish their source version or complete licensing terms. Obtain the corresponding official iflytek distribution and reconcile those files and all other bundled modules before public redistribution.

## WebRTC adapter

`webrtc-player--YuOiwFd.js` contains the WebRTC adapter modules, including `adapter_factory.js` and the browser shims from the [webrtcHacks/adapter project](https://github.com/webrtcHacks/adapter). The exact bundled adapter version could not be established from the minified file.

The upstream [LICENSE.md](https://github.com/webrtcHacks/adapter/blob/master/LICENSE.md) supplies the redistribution conditions and is reproduced in `LICENSE-webrtc-adapter.txt`.
