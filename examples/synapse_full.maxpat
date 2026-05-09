{
    "patcher": {
        "fileversion": 1,
        "appversion": {
            "major": 9,
            "minor": 1,
            "revision": 4,
            "architecture": "x64",
            "modernui": 1
        },
        "classnamespace": "box",
        "rect": [ 617.0, 100.0, 1200.0, 983.0 ],
        "default_fontsize": 11.0,
        "description": "synapse — comprehensive 14-channel OSC receiver. Reads bundles on UDP 9000, parses via synapse_router.js (v8), demuxes by integer channel via [route 1..14] per category.",
        "boxes": [
            {
                "box": {
                    "fontsize": 13.0,
                    "id": "title",
                    "linecount": 2,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 30.0, 15.0, 494.0, 36.0 ],
                    "text": "synapse · MaxMSP receiver  —  14ch audio analyser → OSC bundles on UDP 9000\nOSC parsing happens in synapse_router.js; per-channel demux via [route 1..14]."
                }
            },
            {
                "box": {
                    "id": "status-label",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 760.0, 20.0, 130.0, 19.0 ],
                    "text": "bundles received:"
                }
            },
            {
                "box": {
                    "id": "status-count",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 890.0, 20.0, 80.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "status-tick",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "int" ],
                    "patching_rect": [ 890.0, 50.0, 50.0, 21.0 ],
                    "text": "t b 0"
                }
            },
            {
                "box": {
                    "id": "status-counter",
                    "maxclass": "newobj",
                    "numinlets": 5,
                    "numoutlets": 4,
                    "outlettype": [ "int", "", "", "int" ],
                    "patching_rect": [ 890.0, 78.0, 100.0, 21.0 ],
                    "text": "counter 0 999999"
                }
            },
            {
                "box": {
                    "id": "status-block-label",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 990.0, 20.0, 60.0, 19.0 ],
                    "text": "block #:"
                }
            },
            {
                "box": {
                    "id": "status-block",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1050.0, 20.0, 90.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "udpreceive",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 30.0, 75.0, 130.0, 21.0 ],
                    "text": "udpreceive 9000"
                }
            },
            {
                "box": {
                    "filename": "synapse_router.js",
                    "id": "v8-router",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 10,
                    "outlettype": [ "", "", "", "", "", "", "", "", "", "" ],
                    "patching_rect": [ 30.0, 105.0, 1080.0, 21.0 ],
                    "saved_object_attributes": {
                        "parameter_enable": 0
                    },
                    "text": "v8 synapse_router.js",
                    "textfile": {
                        "filename": "synapse_router.js",
                        "flags": 0,
                        "embed": 0,
                        "autowatch": 1
                    }
                }
            },
            {
                "box": {
                    "id": "hdr-meter",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 30.0, 128.0, 540.0, 19.0 ],
                    "text": "◆ AUDIO  RMS sliders · centroid # · onset bang"
                }
            },
            {
                "box": {
                    "id": "rt-rms",
                    "maxclass": "newobj",
                    "numinlets": 15,
                    "numoutlets": 15,
                    "outlettype": [ "", "", "", "", "", "", "", "", "", "", "", "", "", "", "" ],
                    "patching_rect": [ 30.0, 150.0, 1120.0, 21.0 ],
                    "text": "route 1 2 3 4 5 6 7 8 9 10 11 12 13 14"
                }
            },
            {
                "box": {
                    "id": "rt-centroid",
                    "maxclass": "newobj",
                    "numinlets": 15,
                    "numoutlets": 15,
                    "outlettype": [ "", "", "", "", "", "", "", "", "", "", "", "", "", "", "" ],
                    "patching_rect": [ 30.0, 178.0, 1120.0, 21.0 ],
                    "text": "route 1 2 3 4 5 6 7 8 9 10 11 12 13 14"
                }
            },
            {
                "box": {
                    "id": "rt-onset",
                    "maxclass": "newobj",
                    "numinlets": 15,
                    "numoutlets": 15,
                    "outlettype": [ "", "", "", "", "", "", "", "", "", "", "", "", "", "", "" ],
                    "patching_rect": [ 30.0, 206.0, 1120.0, 21.0 ],
                    "text": "route 1 2 3 4 5 6 7 8 9 10 11 12 13 14"
                }
            },
            {
                "box": {
                    "id": "label-0",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 30.0, 235.0, 75.0, 19.0 ],
                    "text": "ch1"
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "rms-slider-0",
                    "maxclass": "slider",
                    "mult": 300.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 56.5, 257.0, 22.0, 130.0 ],
                    "size": 1.0
                }
            },
            {
                "box": {
                    "id": "centroid-0",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 30.0, 393.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-0",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 55.5, 420.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-thresh-0",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 30.0, 450.0, 50.0, 21.0 ],
                    "text": "> 0.5"
                }
            },
            {
                "box": {
                    "id": "onset-sel-0",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 30.0, 475.0, 40.0, 21.0 ],
                    "text": "sel 1"
                }
            },
            {
                "box": {
                    "id": "label-1",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 110.0, 235.0, 75.0, 19.0 ],
                    "text": "ch2"
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "rms-slider-1",
                    "maxclass": "slider",
                    "mult": 300.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 136.5, 257.0, 22.0, 130.0 ],
                    "size": 1.0
                }
            },
            {
                "box": {
                    "id": "centroid-1",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 110.0, 393.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-1",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 135.5, 420.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-thresh-1",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 110.0, 450.0, 50.0, 21.0 ],
                    "text": "> 0.5"
                }
            },
            {
                "box": {
                    "id": "onset-sel-1",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 110.0, 475.0, 40.0, 21.0 ],
                    "text": "sel 1"
                }
            },
            {
                "box": {
                    "id": "label-2",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 190.0, 235.0, 75.0, 19.0 ],
                    "text": "ch3"
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "rms-slider-2",
                    "maxclass": "slider",
                    "mult": 300.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 216.5, 257.0, 22.0, 130.0 ],
                    "size": 1.0
                }
            },
            {
                "box": {
                    "id": "centroid-2",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 190.0, 393.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-2",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 215.5, 420.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-thresh-2",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 190.0, 450.0, 50.0, 21.0 ],
                    "text": "> 0.5"
                }
            },
            {
                "box": {
                    "id": "onset-sel-2",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 190.0, 475.0, 40.0, 21.0 ],
                    "text": "sel 1"
                }
            },
            {
                "box": {
                    "id": "label-3",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 270.0, 235.0, 75.0, 19.0 ],
                    "text": "ch4"
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "rms-slider-3",
                    "maxclass": "slider",
                    "mult": 300.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 296.5, 257.0, 22.0, 130.0 ],
                    "size": 1.0
                }
            },
            {
                "box": {
                    "id": "centroid-3",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 270.0, 393.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-3",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 295.5, 420.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-thresh-3",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 270.0, 450.0, 50.0, 21.0 ],
                    "text": "> 0.5"
                }
            },
            {
                "box": {
                    "id": "onset-sel-3",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 270.0, 475.0, 40.0, 21.0 ],
                    "text": "sel 1"
                }
            },
            {
                "box": {
                    "id": "label-4",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 350.0, 235.0, 75.0, 19.0 ],
                    "text": "ch5"
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "rms-slider-4",
                    "maxclass": "slider",
                    "mult": 300.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 376.5, 257.0, 22.0, 130.0 ],
                    "size": 1.0
                }
            },
            {
                "box": {
                    "id": "centroid-4",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 350.0, 393.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-4",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 375.5, 420.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-thresh-4",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 350.0, 450.0, 50.0, 21.0 ],
                    "text": "> 0.5"
                }
            },
            {
                "box": {
                    "id": "onset-sel-4",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 350.0, 475.0, 40.0, 21.0 ],
                    "text": "sel 1"
                }
            },
            {
                "box": {
                    "id": "label-5",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 430.0, 235.0, 75.0, 19.0 ],
                    "text": "ch6"
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "rms-slider-5",
                    "maxclass": "slider",
                    "mult": 300.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 456.5, 257.0, 22.0, 130.0 ],
                    "size": 1.0
                }
            },
            {
                "box": {
                    "id": "centroid-5",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 430.0, 393.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-5",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 455.5, 420.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-thresh-5",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 430.0, 450.0, 50.0, 21.0 ],
                    "text": "> 0.5"
                }
            },
            {
                "box": {
                    "id": "onset-sel-5",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 430.0, 475.0, 40.0, 21.0 ],
                    "text": "sel 1"
                }
            },
            {
                "box": {
                    "id": "label-6",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 510.0, 235.0, 75.0, 19.0 ],
                    "text": "ch7"
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "rms-slider-6",
                    "maxclass": "slider",
                    "mult": 300.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 536.5, 257.0, 22.0, 130.0 ],
                    "size": 1.0
                }
            },
            {
                "box": {
                    "id": "centroid-6",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 510.0, 393.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-6",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 535.5, 420.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-thresh-6",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 510.0, 450.0, 50.0, 21.0 ],
                    "text": "> 0.5"
                }
            },
            {
                "box": {
                    "id": "onset-sel-6",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 510.0, 475.0, 40.0, 21.0 ],
                    "text": "sel 1"
                }
            },
            {
                "box": {
                    "id": "label-7",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 590.0, 235.0, 75.0, 19.0 ],
                    "text": "ch8"
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "rms-slider-7",
                    "maxclass": "slider",
                    "mult": 300.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 616.5, 257.0, 22.0, 130.0 ],
                    "size": 1.0
                }
            },
            {
                "box": {
                    "id": "centroid-7",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 590.0, 393.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-7",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 615.5, 420.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-thresh-7",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 590.0, 450.0, 50.0, 21.0 ],
                    "text": "> 0.5"
                }
            },
            {
                "box": {
                    "id": "onset-sel-7",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 590.0, 475.0, 40.0, 21.0 ],
                    "text": "sel 1"
                }
            },
            {
                "box": {
                    "id": "label-8",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 670.0, 235.0, 75.0, 19.0 ],
                    "text": "ch9"
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "rms-slider-8",
                    "maxclass": "slider",
                    "mult": 300.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 696.5, 257.0, 22.0, 130.0 ],
                    "size": 1.0
                }
            },
            {
                "box": {
                    "id": "centroid-8",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 670.0, 393.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-8",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 695.5, 420.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-thresh-8",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 670.0, 450.0, 50.0, 21.0 ],
                    "text": "> 0.5"
                }
            },
            {
                "box": {
                    "id": "onset-sel-8",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 670.0, 475.0, 40.0, 21.0 ],
                    "text": "sel 1"
                }
            },
            {
                "box": {
                    "id": "label-9",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 750.0, 235.0, 75.0, 19.0 ],
                    "text": "ch10"
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "rms-slider-9",
                    "maxclass": "slider",
                    "mult": 300.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 776.5, 257.0, 22.0, 130.0 ],
                    "size": 1.0
                }
            },
            {
                "box": {
                    "id": "centroid-9",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 750.0, 393.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-9",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 775.5, 420.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-thresh-9",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 750.0, 450.0, 50.0, 21.0 ],
                    "text": "> 0.5"
                }
            },
            {
                "box": {
                    "id": "onset-sel-9",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 750.0, 475.0, 40.0, 21.0 ],
                    "text": "sel 1"
                }
            },
            {
                "box": {
                    "id": "label-10",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 830.0, 235.0, 75.0, 19.0 ],
                    "text": "ch11"
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "rms-slider-10",
                    "maxclass": "slider",
                    "mult": 300.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 856.5, 257.0, 22.0, 130.0 ],
                    "size": 1.0
                }
            },
            {
                "box": {
                    "id": "centroid-10",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 830.0, 393.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-10",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 855.5, 420.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-thresh-10",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 830.0, 450.0, 50.0, 21.0 ],
                    "text": "> 0.5"
                }
            },
            {
                "box": {
                    "id": "onset-sel-10",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 830.0, 475.0, 40.0, 21.0 ],
                    "text": "sel 1"
                }
            },
            {
                "box": {
                    "id": "label-11",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 910.0, 235.0, 75.0, 19.0 ],
                    "text": "ch12"
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "rms-slider-11",
                    "maxclass": "slider",
                    "mult": 300.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 936.5, 257.0, 22.0, 130.0 ],
                    "size": 1.0
                }
            },
            {
                "box": {
                    "id": "centroid-11",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 910.0, 393.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-11",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 935.5, 420.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-thresh-11",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 910.0, 450.0, 50.0, 21.0 ],
                    "text": "> 0.5"
                }
            },
            {
                "box": {
                    "id": "onset-sel-11",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 910.0, 475.0, 40.0, 21.0 ],
                    "text": "sel 1"
                }
            },
            {
                "box": {
                    "id": "label-12",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 990.0, 235.0, 75.0, 19.0 ],
                    "text": "ch13"
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "rms-slider-12",
                    "maxclass": "slider",
                    "mult": 300.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1016.5, 257.0, 22.0, 130.0 ],
                    "size": 1.0
                }
            },
            {
                "box": {
                    "id": "centroid-12",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 990.0, 393.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-12",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1015.5, 420.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-thresh-12",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 990.0, 450.0, 50.0, 21.0 ],
                    "text": "> 0.5"
                }
            },
            {
                "box": {
                    "id": "onset-sel-12",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 990.0, 475.0, 40.0, 21.0 ],
                    "text": "sel 1"
                }
            },
            {
                "box": {
                    "id": "label-13",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1070.0, 235.0, 75.0, 19.0 ],
                    "text": "ch14"
                }
            },
            {
                "box": {
                    "floatoutput": 1,
                    "id": "rms-slider-13",
                    "maxclass": "slider",
                    "mult": 300.0,
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1096.5, 257.0, 22.0, 130.0 ],
                    "size": 1.0
                }
            },
            {
                "box": {
                    "id": "centroid-13",
                    "maxclass": "number",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1070.0, 393.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-13",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1095.5, 420.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "onset-thresh-13",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "patching_rect": [ 1070.0, 450.0, 50.0, 21.0 ],
                    "text": "> 0.5"
                }
            },
            {
                "box": {
                    "id": "onset-sel-13",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "bang", "" ],
                    "patching_rect": [ 1070.0, 475.0, 40.0, 21.0 ],
                    "text": "sel 1"
                }
            },
            {
                "box": {
                    "id": "hdr-cv",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 30.0, 503.0, 540.0, 19.0 ],
                    "text": "◆ CV  smoothed DC value · rate of change"
                }
            },
            {
                "box": {
                    "id": "rt-cv",
                    "maxclass": "newobj",
                    "numinlets": 15,
                    "numoutlets": 15,
                    "outlettype": [ "", "", "", "", "", "", "", "", "", "", "", "", "", "", "" ],
                    "patching_rect": [ 30.0, 525.0, 1120.0, 21.0 ],
                    "text": "route 1 2 3 4 5 6 7 8 9 10 11 12 13 14"
                }
            },
            {
                "box": {
                    "id": "rt-cv-rate",
                    "maxclass": "newobj",
                    "numinlets": 15,
                    "numoutlets": 15,
                    "outlettype": [ "", "", "", "", "", "", "", "", "", "", "", "", "", "", "" ],
                    "patching_rect": [ 30.0, 553.0, 1120.0, 21.0 ],
                    "text": "route 1 2 3 4 5 6 7 8 9 10 11 12 13 14"
                }
            },
            {
                "box": {
                    "id": "cv-label-0",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 30.0, 585.0, 75.0, 19.0 ],
                    "text": "ch1"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-val-0",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 30.0, 607.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-rate-0",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 30.0, 633.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "cv-label-1",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 110.0, 585.0, 75.0, 19.0 ],
                    "text": "ch2"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-val-1",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 110.0, 607.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-rate-1",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 110.0, 633.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "cv-label-2",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 190.0, 585.0, 75.0, 19.0 ],
                    "text": "ch3"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-val-2",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 190.0, 607.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-rate-2",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 190.0, 633.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "cv-label-3",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 270.0, 585.0, 75.0, 19.0 ],
                    "text": "ch4"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-val-3",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 270.0, 607.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-rate-3",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 270.0, 633.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "cv-label-4",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 350.0, 585.0, 75.0, 19.0 ],
                    "text": "ch5"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-val-4",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 350.0, 607.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-rate-4",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 350.0, 633.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "cv-label-5",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 430.0, 585.0, 75.0, 19.0 ],
                    "text": "ch6"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-val-5",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 430.0, 607.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-rate-5",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 430.0, 633.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "cv-label-6",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 510.0, 585.0, 75.0, 19.0 ],
                    "text": "ch7"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-val-6",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 510.0, 607.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-rate-6",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 510.0, 633.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "cv-label-7",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 590.0, 585.0, 75.0, 19.0 ],
                    "text": "ch8"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-val-7",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 590.0, 607.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-rate-7",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 590.0, 633.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "cv-label-8",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 670.0, 585.0, 75.0, 19.0 ],
                    "text": "ch9"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-val-8",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 670.0, 607.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-rate-8",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 670.0, 633.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "cv-label-9",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 750.0, 585.0, 75.0, 19.0 ],
                    "text": "ch10"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-val-9",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 750.0, 607.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-rate-9",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 750.0, 633.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "cv-label-10",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 830.0, 585.0, 75.0, 19.0 ],
                    "text": "ch11"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-val-10",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 830.0, 607.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-rate-10",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 830.0, 633.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "cv-label-11",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 910.0, 585.0, 75.0, 19.0 ],
                    "text": "ch12"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-val-11",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 910.0, 607.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-rate-11",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 910.0, 633.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "cv-label-12",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 990.0, 585.0, 75.0, 19.0 ],
                    "text": "ch13"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-val-12",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 990.0, 607.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-rate-12",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 990.0, 633.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "cv-label-13",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1070.0, 585.0, 75.0, 19.0 ],
                    "text": "ch14"
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-val-13",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1070.0, 607.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "format": 6,
                    "id": "cv-rate-13",
                    "maxclass": "flonum",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1070.0, 633.0, 75.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "hdr-gate",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 30.0, 663.0, 540.0, 19.0 ],
                    "text": "◆ GATE  state toggle · edge bang (any rising/falling edge)"
                }
            },
            {
                "box": {
                    "id": "rt-gate",
                    "maxclass": "newobj",
                    "numinlets": 15,
                    "numoutlets": 15,
                    "outlettype": [ "", "", "", "", "", "", "", "", "", "", "", "", "", "", "" ],
                    "patching_rect": [ 30.0, 685.0, 1120.0, 21.0 ],
                    "text": "route 1 2 3 4 5 6 7 8 9 10 11 12 13 14"
                }
            },
            {
                "box": {
                    "id": "rt-gate-event",
                    "maxclass": "newobj",
                    "numinlets": 15,
                    "numoutlets": 15,
                    "outlettype": [ "", "", "", "", "", "", "", "", "", "", "", "", "", "", "" ],
                    "patching_rect": [ 30.0, 713.0, 1120.0, 21.0 ],
                    "text": "route 1 2 3 4 5 6 7 8 9 10 11 12 13 14"
                }
            },
            {
                "box": {
                    "id": "gate-label-0",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 30.0, 745.0, 75.0, 19.0 ],
                    "text": "ch1"
                }
            },
            {
                "box": {
                    "id": "gate-toggle-0",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 53.5, 767.0, 28.0, 28.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-edge-0",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 55.5, 801.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-label-1",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 110.0, 745.0, 75.0, 19.0 ],
                    "text": "ch2"
                }
            },
            {
                "box": {
                    "id": "gate-toggle-1",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 133.5, 767.0, 28.0, 28.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-edge-1",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 135.5, 801.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-label-2",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 190.0, 745.0, 75.0, 19.0 ],
                    "text": "ch3"
                }
            },
            {
                "box": {
                    "id": "gate-toggle-2",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 213.5, 767.0, 28.0, 28.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-edge-2",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 215.5, 801.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-label-3",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 270.0, 745.0, 75.0, 19.0 ],
                    "text": "ch4"
                }
            },
            {
                "box": {
                    "id": "gate-toggle-3",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 293.5, 767.0, 28.0, 28.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-edge-3",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 295.5, 801.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-label-4",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 350.0, 745.0, 75.0, 19.0 ],
                    "text": "ch5"
                }
            },
            {
                "box": {
                    "id": "gate-toggle-4",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 373.5, 767.0, 28.0, 28.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-edge-4",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 375.5, 801.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-label-5",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 430.0, 745.0, 75.0, 19.0 ],
                    "text": "ch6"
                }
            },
            {
                "box": {
                    "id": "gate-toggle-5",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 453.5, 767.0, 28.0, 28.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-edge-5",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 455.5, 801.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-label-6",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 510.0, 745.0, 75.0, 19.0 ],
                    "text": "ch7"
                }
            },
            {
                "box": {
                    "id": "gate-toggle-6",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 533.5, 767.0, 28.0, 28.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-edge-6",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 535.5, 801.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-label-7",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 590.0, 745.0, 75.0, 19.0 ],
                    "text": "ch8"
                }
            },
            {
                "box": {
                    "id": "gate-toggle-7",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 613.5, 767.0, 28.0, 28.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-edge-7",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 615.5, 801.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-label-8",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 670.0, 745.0, 75.0, 19.0 ],
                    "text": "ch9"
                }
            },
            {
                "box": {
                    "id": "gate-toggle-8",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 693.5, 767.0, 28.0, 28.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-edge-8",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 695.5, 801.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-label-9",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 750.0, 745.0, 75.0, 19.0 ],
                    "text": "ch10"
                }
            },
            {
                "box": {
                    "id": "gate-toggle-9",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 773.5, 767.0, 28.0, 28.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-edge-9",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 775.5, 801.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-label-10",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 830.0, 745.0, 75.0, 19.0 ],
                    "text": "ch11"
                }
            },
            {
                "box": {
                    "id": "gate-toggle-10",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 853.5, 767.0, 28.0, 28.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-edge-10",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 855.5, 801.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-label-11",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 910.0, 745.0, 75.0, 19.0 ],
                    "text": "ch12"
                }
            },
            {
                "box": {
                    "id": "gate-toggle-11",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 933.5, 767.0, 28.0, 28.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-edge-11",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 935.5, 801.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-label-12",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 990.0, 745.0, 75.0, 19.0 ],
                    "text": "ch13"
                }
            },
            {
                "box": {
                    "id": "gate-toggle-12",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1013.5, 767.0, 28.0, 28.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-edge-12",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1015.5, 801.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-label-13",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1070.0, 745.0, 75.0, 19.0 ],
                    "text": "ch14"
                }
            },
            {
                "box": {
                    "id": "gate-toggle-13",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1093.5, 767.0, 28.0, 28.0 ]
                }
            },
            {
                "box": {
                    "id": "gate-edge-13",
                    "maxclass": "button",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1095.5, 801.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "hdr-spec",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 37.5, 827.0, 700.0, 19.0 ],
                    "text": "◆ SPECTRUM  pick a channel (only audio-role channels emit) · 32 log-spaced bins · ~30Hz"
                }
            },
            {
                "box": {
                    "id": "spec-menu",
                    "items": [ "ch1", ",", "ch2", ",", "ch3", ",", "ch4", ",", "ch5", ",", "ch6", ",", "ch7", ",", "ch8", ",", "ch9", ",", "ch10", ",", "ch11", ",", "ch12", ",", "ch13", ",", "ch14" ],
                    "maxclass": "umenu",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "int", "", "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 30.0, 856.0, 100.0, 21.0 ]
                }
            },
            {
                "box": {
                    "id": "spec-menu-label",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 140.0, 857.0, 600.0, 19.0 ],
                    "text": "← select channel  (sent to v8 inlet 1; JS converts 0-based umenu int to 1-based ch)"
                }
            },
            {
                "box": {
                    "bgcolor": [ 0.094, 0.094, 0.094, 1.0 ],
                    "contdata": 1,
                    "id": "spec-multi",
                    "maxclass": "multislider",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 30.0, 890.0, 1080.0, 120.0 ],
                    "setminmax": [ 0.0, 1.0 ],
                    "size": 32,
                    "slidercolor": [ 0.984, 0.949, 0.831, 1.0 ]
                }
            },
            {
                "box": {
                    "id": "hdr-clap",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 30.0, 1008.0, 700.0, 19.0 ],
                    "text": "◆ CLAP  512-D audio embedding (slow tier ~1Hz, only when --clap is on)"
                }
            },
            {
                "box": {
                    "bgcolor": [ 0.094, 0.094, 0.094, 1.0 ],
                    "contdata": 1,
                    "id": "clap-multi",
                    "maxclass": "multislider",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 30.0, 1030.0, 1080.0, 80.0 ],
                    "size": 512,
                    "slidercolor": [ 0.65, 0.85, 0.95, 1.0 ]
                }
            },
            {
                "box": {
                    "id": "clap-zl",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 2,
                    "outlettype": [ "", "" ],
                    "patching_rect": [ 30.0, 1120.0, 130.0, 21.0 ],
                    "text": "zl group 512"
                }
            },
            {
                "box": {
                    "id": "footer",
                    "linecount": 4,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 30.0, 1160.0, 397.0, 56.0 ],
                    "text": "Forward to Unreal:  add a [udpsend <unreal-host> <unreal-port>] and tap any of\nthe [route 1..14] outlets above (or the v8 category outlets directly).\n/synapse/cv/N for slow control, /gate/N for triggers, /spectrum/N for the bin lists.\nFull schema: docs/OSC_SCHEMA.md."
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "destination": [ "clap-multi", 0 ],
                    "source": [ "clap-zl", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-0", 0 ],
                    "source": [ "onset-sel-0", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-1", 0 ],
                    "source": [ "onset-sel-1", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-10", 0 ],
                    "source": [ "onset-sel-10", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-11", 0 ],
                    "source": [ "onset-sel-11", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-12", 0 ],
                    "source": [ "onset-sel-12", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-13", 0 ],
                    "source": [ "onset-sel-13", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-2", 0 ],
                    "source": [ "onset-sel-2", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-3", 0 ],
                    "source": [ "onset-sel-3", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-4", 0 ],
                    "source": [ "onset-sel-4", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-5", 0 ],
                    "source": [ "onset-sel-5", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-6", 0 ],
                    "source": [ "onset-sel-6", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-7", 0 ],
                    "source": [ "onset-sel-7", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-8", 0 ],
                    "source": [ "onset-sel-8", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-9", 0 ],
                    "source": [ "onset-sel-9", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-sel-0", 0 ],
                    "source": [ "onset-thresh-0", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-sel-1", 0 ],
                    "source": [ "onset-thresh-1", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-sel-10", 0 ],
                    "source": [ "onset-thresh-10", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-sel-11", 0 ],
                    "source": [ "onset-thresh-11", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-sel-12", 0 ],
                    "source": [ "onset-thresh-12", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-sel-13", 0 ],
                    "source": [ "onset-thresh-13", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-sel-2", 0 ],
                    "source": [ "onset-thresh-2", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-sel-3", 0 ],
                    "source": [ "onset-thresh-3", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-sel-4", 0 ],
                    "source": [ "onset-thresh-4", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-sel-5", 0 ],
                    "source": [ "onset-thresh-5", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-sel-6", 0 ],
                    "source": [ "onset-thresh-6", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-sel-7", 0 ],
                    "source": [ "onset-thresh-7", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-sel-8", 0 ],
                    "source": [ "onset-thresh-8", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-sel-9", 0 ],
                    "source": [ "onset-thresh-9", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "centroid-0", 0 ],
                    "source": [ "rt-centroid", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "centroid-1", 0 ],
                    "source": [ "rt-centroid", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "centroid-10", 0 ],
                    "source": [ "rt-centroid", 10 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "centroid-11", 0 ],
                    "source": [ "rt-centroid", 11 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "centroid-12", 0 ],
                    "source": [ "rt-centroid", 12 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "centroid-13", 0 ],
                    "source": [ "rt-centroid", 13 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "centroid-2", 0 ],
                    "source": [ "rt-centroid", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "centroid-3", 0 ],
                    "source": [ "rt-centroid", 3 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "centroid-4", 0 ],
                    "source": [ "rt-centroid", 4 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "centroid-5", 0 ],
                    "source": [ "rt-centroid", 5 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "centroid-6", 0 ],
                    "source": [ "rt-centroid", 6 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "centroid-7", 0 ],
                    "source": [ "rt-centroid", 7 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "centroid-8", 0 ],
                    "source": [ "rt-centroid", 8 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "centroid-9", 0 ],
                    "source": [ "rt-centroid", 9 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-val-0", 0 ],
                    "source": [ "rt-cv", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-val-1", 0 ],
                    "source": [ "rt-cv", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-val-10", 0 ],
                    "source": [ "rt-cv", 10 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-val-11", 0 ],
                    "source": [ "rt-cv", 11 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-val-12", 0 ],
                    "source": [ "rt-cv", 12 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-val-13", 0 ],
                    "source": [ "rt-cv", 13 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-val-2", 0 ],
                    "source": [ "rt-cv", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-val-3", 0 ],
                    "source": [ "rt-cv", 3 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-val-4", 0 ],
                    "source": [ "rt-cv", 4 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-val-5", 0 ],
                    "source": [ "rt-cv", 5 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-val-6", 0 ],
                    "source": [ "rt-cv", 6 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-val-7", 0 ],
                    "source": [ "rt-cv", 7 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-val-8", 0 ],
                    "source": [ "rt-cv", 8 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-val-9", 0 ],
                    "source": [ "rt-cv", 9 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-rate-0", 0 ],
                    "source": [ "rt-cv-rate", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-rate-1", 0 ],
                    "source": [ "rt-cv-rate", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-rate-10", 0 ],
                    "source": [ "rt-cv-rate", 10 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-rate-11", 0 ],
                    "source": [ "rt-cv-rate", 11 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-rate-12", 0 ],
                    "source": [ "rt-cv-rate", 12 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-rate-13", 0 ],
                    "source": [ "rt-cv-rate", 13 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-rate-2", 0 ],
                    "source": [ "rt-cv-rate", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-rate-3", 0 ],
                    "source": [ "rt-cv-rate", 3 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-rate-4", 0 ],
                    "source": [ "rt-cv-rate", 4 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-rate-5", 0 ],
                    "source": [ "rt-cv-rate", 5 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-rate-6", 0 ],
                    "source": [ "rt-cv-rate", 6 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-rate-7", 0 ],
                    "source": [ "rt-cv-rate", 7 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-rate-8", 0 ],
                    "source": [ "rt-cv-rate", 8 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "cv-rate-9", 0 ],
                    "source": [ "rt-cv-rate", 9 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-toggle-0", 0 ],
                    "source": [ "rt-gate", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-toggle-1", 0 ],
                    "source": [ "rt-gate", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-toggle-10", 0 ],
                    "source": [ "rt-gate", 10 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-toggle-11", 0 ],
                    "source": [ "rt-gate", 11 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-toggle-12", 0 ],
                    "source": [ "rt-gate", 12 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-toggle-13", 0 ],
                    "source": [ "rt-gate", 13 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-toggle-2", 0 ],
                    "source": [ "rt-gate", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-toggle-3", 0 ],
                    "source": [ "rt-gate", 3 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-toggle-4", 0 ],
                    "source": [ "rt-gate", 4 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-toggle-5", 0 ],
                    "source": [ "rt-gate", 5 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-toggle-6", 0 ],
                    "source": [ "rt-gate", 6 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-toggle-7", 0 ],
                    "source": [ "rt-gate", 7 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-toggle-8", 0 ],
                    "source": [ "rt-gate", 8 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-toggle-9", 0 ],
                    "source": [ "rt-gate", 9 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-edge-0", 0 ],
                    "source": [ "rt-gate-event", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-edge-1", 0 ],
                    "source": [ "rt-gate-event", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-edge-10", 0 ],
                    "source": [ "rt-gate-event", 10 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-edge-11", 0 ],
                    "source": [ "rt-gate-event", 11 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-edge-12", 0 ],
                    "source": [ "rt-gate-event", 12 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-edge-13", 0 ],
                    "source": [ "rt-gate-event", 13 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-edge-2", 0 ],
                    "source": [ "rt-gate-event", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-edge-3", 0 ],
                    "source": [ "rt-gate-event", 3 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-edge-4", 0 ],
                    "source": [ "rt-gate-event", 4 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-edge-5", 0 ],
                    "source": [ "rt-gate-event", 5 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-edge-6", 0 ],
                    "source": [ "rt-gate-event", 6 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-edge-7", 0 ],
                    "source": [ "rt-gate-event", 7 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-edge-8", 0 ],
                    "source": [ "rt-gate-event", 8 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "gate-edge-9", 0 ],
                    "source": [ "rt-gate-event", 9 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-thresh-0", 0 ],
                    "source": [ "rt-onset", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-thresh-1", 0 ],
                    "source": [ "rt-onset", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-thresh-10", 0 ],
                    "source": [ "rt-onset", 10 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-thresh-11", 0 ],
                    "source": [ "rt-onset", 11 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-thresh-12", 0 ],
                    "source": [ "rt-onset", 12 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-thresh-13", 0 ],
                    "source": [ "rt-onset", 13 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-thresh-2", 0 ],
                    "source": [ "rt-onset", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-thresh-3", 0 ],
                    "source": [ "rt-onset", 3 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-thresh-4", 0 ],
                    "source": [ "rt-onset", 4 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-thresh-5", 0 ],
                    "source": [ "rt-onset", 5 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-thresh-6", 0 ],
                    "source": [ "rt-onset", 6 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-thresh-7", 0 ],
                    "source": [ "rt-onset", 7 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-thresh-8", 0 ],
                    "source": [ "rt-onset", 8 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "onset-thresh-9", 0 ],
                    "source": [ "rt-onset", 9 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rms-slider-0", 0 ],
                    "source": [ "rt-rms", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rms-slider-1", 0 ],
                    "source": [ "rt-rms", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rms-slider-10", 0 ],
                    "source": [ "rt-rms", 10 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rms-slider-11", 0 ],
                    "source": [ "rt-rms", 11 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rms-slider-12", 0 ],
                    "source": [ "rt-rms", 12 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rms-slider-13", 0 ],
                    "source": [ "rt-rms", 13 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rms-slider-2", 0 ],
                    "source": [ "rt-rms", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rms-slider-3", 0 ],
                    "source": [ "rt-rms", 3 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rms-slider-4", 0 ],
                    "source": [ "rt-rms", 4 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rms-slider-5", 0 ],
                    "source": [ "rt-rms", 5 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rms-slider-6", 0 ],
                    "source": [ "rt-rms", 6 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rms-slider-7", 0 ],
                    "source": [ "rt-rms", 7 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rms-slider-8", 0 ],
                    "source": [ "rt-rms", 8 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rms-slider-9", 0 ],
                    "source": [ "rt-rms", 9 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "v8-router", 1 ],
                    "source": [ "spec-menu", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "status-count", 0 ],
                    "source": [ "status-counter", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "status-counter", 0 ],
                    "source": [ "status-tick", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "v8-router", 0 ],
                    "source": [ "udpreceive", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "clap-zl", 0 ],
                    "source": [ "v8-router", 9 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rt-centroid", 0 ],
                    "source": [ "v8-router", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rt-cv", 0 ],
                    "source": [ "v8-router", 3 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rt-cv-rate", 0 ],
                    "source": [ "v8-router", 4 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rt-gate", 0 ],
                    "source": [ "v8-router", 5 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rt-gate-event", 0 ],
                    "source": [ "v8-router", 6 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rt-onset", 0 ],
                    "source": [ "v8-router", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "rt-rms", 0 ],
                    "source": [ "v8-router", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "spec-multi", 0 ],
                    "source": [ "v8-router", 7 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "status-block", 0 ],
                    "order": 0,
                    "source": [ "v8-router", 8 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "status-tick", 0 ],
                    "order": 1,
                    "source": [ "v8-router", 8 ]
                }
            }
        ],
        "autosave": 0
    }
}