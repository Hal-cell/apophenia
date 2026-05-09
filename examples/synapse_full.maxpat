{
	"patcher": {
		"fileversion": 1,
		"appversion": {
			"major": 8,
			"minor": 6,
			"revision": 0,
			"architecture": "x64",
			"modernui": 1
		},
		"classnamespace": "box",
		"rect": [
			60.0,
			60.0,
			1200.0,
			1250
		],
		"bglocked": 0,
		"openinpresentation": 0,
		"default_fontsize": 11.0,
		"default_fontface": 0,
		"default_fontname": "Arial",
		"gridonopen": 1,
		"gridsize": [
			15.0,
			15.0
		],
		"gridsnaponopen": 1,
		"objectsnaponopen": 1,
		"statusbarvisible": 2,
		"toolbarvisible": 1,
		"lefttoolbarpinned": 0,
		"toptoolbarpinned": 0,
		"righttoolbarpinned": 0,
		"bottomtoolbarpinned": 0,
		"toolbars_unpinned_last_save": 0,
		"tallnewobj": 0,
		"boxanimatetime": 200,
		"enablehscroll": 1,
		"enablevscroll": 1,
		"devicewidth": 0.0,
		"description": "synapse \u2014 comprehensive 14-channel OSC receiver. Reads bundles on UDP 9000, parses via synapse_router.js (v8), demuxes by integer channel via [route 1..14] per category.",
		"digest": "",
		"tags": "",
		"style": "",
		"subpatcher_template": "",
		"assistshowspatchername": 0,
		"boxes": [
			{
				"box": {
					"id": "title",
					"maxclass": "comment",
					"text": "synapse \u00b7 MaxMSP receiver  \u2014  14ch audio analyser \u2192 OSC bundles on UDP 9000\nOSC parsing happens in synapse_router.js; per-channel demux via [route 1..14].",
					"patching_rect": [
						30.0,
						15.0,
						700.0,
						40.0
					],
					"fontsize": 13.0,
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "status-label",
					"maxclass": "comment",
					"text": "bundles received:",
					"patching_rect": [
						760.0,
						20.0,
						130.0,
						20.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "status-count",
					"maxclass": "number",
					"patching_rect": [
						890.0,
						20.0,
						80.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "status-tick",
					"maxclass": "newobj",
					"text": "t b 0",
					"patching_rect": [
						890.0,
						50.0,
						50.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						"int"
					]
				}
			},
			{
				"box": {
					"id": "status-counter",
					"maxclass": "newobj",
					"text": "counter 0 999999",
					"patching_rect": [
						890.0,
						78.0,
						100.0,
						22.0
					],
					"numinlets": 5,
					"numoutlets": 4,
					"outlettype": [
						"int",
						"",
						"",
						"int"
					]
				}
			},
			{
				"box": {
					"id": "status-block-label",
					"maxclass": "comment",
					"text": "block #:",
					"patching_rect": [
						990.0,
						20.0,
						60.0,
						20.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "status-block",
					"maxclass": "number",
					"patching_rect": [
						1050.0,
						20.0,
						90.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "udpreceive",
					"maxclass": "newobj",
					"text": "udpreceive 9000",
					"patching_rect": [
						30.0,
						75.0,
						130.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "v8-router",
					"maxclass": "newobj",
					"text": "v8 synapse_router.js",
					"patching_rect": [
						30.0,
						105.0,
						1080.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 10,
					"outlettype": [
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "hdr-meter",
					"maxclass": "comment",
					"text": "\u25c6 AUDIO  RMS sliders \u00b7 centroid # \u00b7 onset bang",
					"patching_rect": [
						30.0,
						128,
						540.0,
						20.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rt-rms",
					"maxclass": "newobj",
					"text": "route 1 2 3 4 5 6 7 8 9 10 11 12 13 14",
					"patching_rect": [
						30,
						150,
						1120,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 15,
					"outlettype": [
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "rt-centroid",
					"maxclass": "newobj",
					"text": "route 1 2 3 4 5 6 7 8 9 10 11 12 13 14",
					"patching_rect": [
						30,
						178,
						1120,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 15,
					"outlettype": [
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "rt-onset",
					"maxclass": "newobj",
					"text": "route 1 2 3 4 5 6 7 8 9 10 11 12 13 14",
					"patching_rect": [
						30,
						206,
						1120,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 15,
					"outlettype": [
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "label-0",
					"maxclass": "comment",
					"text": "ch1",
					"patching_rect": [
						30,
						235,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rms-slider-0",
					"maxclass": "slider",
					"patching_rect": [
						56.5,
						257,
						22.0,
						130.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"size": 128,
					"floatoutput": 0,
					"min": 0.0,
					"mult": 300.0
				}
			},
			{
				"box": {
					"id": "centroid-0",
					"maxclass": "number",
					"patching_rect": [
						30,
						393,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-0",
					"maxclass": "button",
					"patching_rect": [
						55.5,
						420,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-thresh-0",
					"maxclass": "newobj",
					"text": "> 0.5",
					"patching_rect": [
						30,
						450,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "onset-sel-0",
					"maxclass": "newobj",
					"text": "sel 1",
					"patching_rect": [
						30,
						475,
						40.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						""
					]
				}
			},
			{
				"box": {
					"id": "label-1",
					"maxclass": "comment",
					"text": "ch2",
					"patching_rect": [
						110,
						235,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rms-slider-1",
					"maxclass": "slider",
					"patching_rect": [
						136.5,
						257,
						22.0,
						130.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"size": 128,
					"floatoutput": 0,
					"min": 0.0,
					"mult": 300.0
				}
			},
			{
				"box": {
					"id": "centroid-1",
					"maxclass": "number",
					"patching_rect": [
						110,
						393,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-1",
					"maxclass": "button",
					"patching_rect": [
						135.5,
						420,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-thresh-1",
					"maxclass": "newobj",
					"text": "> 0.5",
					"patching_rect": [
						110,
						450,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "onset-sel-1",
					"maxclass": "newobj",
					"text": "sel 1",
					"patching_rect": [
						110,
						475,
						40.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						""
					]
				}
			},
			{
				"box": {
					"id": "label-2",
					"maxclass": "comment",
					"text": "ch3",
					"patching_rect": [
						190,
						235,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rms-slider-2",
					"maxclass": "slider",
					"patching_rect": [
						216.5,
						257,
						22.0,
						130.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"size": 128,
					"floatoutput": 0,
					"min": 0.0,
					"mult": 300.0
				}
			},
			{
				"box": {
					"id": "centroid-2",
					"maxclass": "number",
					"patching_rect": [
						190,
						393,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-2",
					"maxclass": "button",
					"patching_rect": [
						215.5,
						420,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-thresh-2",
					"maxclass": "newobj",
					"text": "> 0.5",
					"patching_rect": [
						190,
						450,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "onset-sel-2",
					"maxclass": "newobj",
					"text": "sel 1",
					"patching_rect": [
						190,
						475,
						40.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						""
					]
				}
			},
			{
				"box": {
					"id": "label-3",
					"maxclass": "comment",
					"text": "ch4",
					"patching_rect": [
						270,
						235,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rms-slider-3",
					"maxclass": "slider",
					"patching_rect": [
						296.5,
						257,
						22.0,
						130.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"size": 128,
					"floatoutput": 0,
					"min": 0.0,
					"mult": 300.0
				}
			},
			{
				"box": {
					"id": "centroid-3",
					"maxclass": "number",
					"patching_rect": [
						270,
						393,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-3",
					"maxclass": "button",
					"patching_rect": [
						295.5,
						420,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-thresh-3",
					"maxclass": "newobj",
					"text": "> 0.5",
					"patching_rect": [
						270,
						450,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "onset-sel-3",
					"maxclass": "newobj",
					"text": "sel 1",
					"patching_rect": [
						270,
						475,
						40.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						""
					]
				}
			},
			{
				"box": {
					"id": "label-4",
					"maxclass": "comment",
					"text": "ch5",
					"patching_rect": [
						350,
						235,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rms-slider-4",
					"maxclass": "slider",
					"patching_rect": [
						376.5,
						257,
						22.0,
						130.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"size": 128,
					"floatoutput": 0,
					"min": 0.0,
					"mult": 300.0
				}
			},
			{
				"box": {
					"id": "centroid-4",
					"maxclass": "number",
					"patching_rect": [
						350,
						393,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-4",
					"maxclass": "button",
					"patching_rect": [
						375.5,
						420,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-thresh-4",
					"maxclass": "newobj",
					"text": "> 0.5",
					"patching_rect": [
						350,
						450,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "onset-sel-4",
					"maxclass": "newobj",
					"text": "sel 1",
					"patching_rect": [
						350,
						475,
						40.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						""
					]
				}
			},
			{
				"box": {
					"id": "label-5",
					"maxclass": "comment",
					"text": "ch6",
					"patching_rect": [
						430,
						235,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rms-slider-5",
					"maxclass": "slider",
					"patching_rect": [
						456.5,
						257,
						22.0,
						130.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"size": 128,
					"floatoutput": 0,
					"min": 0.0,
					"mult": 300.0
				}
			},
			{
				"box": {
					"id": "centroid-5",
					"maxclass": "number",
					"patching_rect": [
						430,
						393,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-5",
					"maxclass": "button",
					"patching_rect": [
						455.5,
						420,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-thresh-5",
					"maxclass": "newobj",
					"text": "> 0.5",
					"patching_rect": [
						430,
						450,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "onset-sel-5",
					"maxclass": "newobj",
					"text": "sel 1",
					"patching_rect": [
						430,
						475,
						40.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						""
					]
				}
			},
			{
				"box": {
					"id": "label-6",
					"maxclass": "comment",
					"text": "ch7",
					"patching_rect": [
						510,
						235,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rms-slider-6",
					"maxclass": "slider",
					"patching_rect": [
						536.5,
						257,
						22.0,
						130.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"size": 128,
					"floatoutput": 0,
					"min": 0.0,
					"mult": 300.0
				}
			},
			{
				"box": {
					"id": "centroid-6",
					"maxclass": "number",
					"patching_rect": [
						510,
						393,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-6",
					"maxclass": "button",
					"patching_rect": [
						535.5,
						420,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-thresh-6",
					"maxclass": "newobj",
					"text": "> 0.5",
					"patching_rect": [
						510,
						450,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "onset-sel-6",
					"maxclass": "newobj",
					"text": "sel 1",
					"patching_rect": [
						510,
						475,
						40.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						""
					]
				}
			},
			{
				"box": {
					"id": "label-7",
					"maxclass": "comment",
					"text": "ch8",
					"patching_rect": [
						590,
						235,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rms-slider-7",
					"maxclass": "slider",
					"patching_rect": [
						616.5,
						257,
						22.0,
						130.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"size": 128,
					"floatoutput": 0,
					"min": 0.0,
					"mult": 300.0
				}
			},
			{
				"box": {
					"id": "centroid-7",
					"maxclass": "number",
					"patching_rect": [
						590,
						393,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-7",
					"maxclass": "button",
					"patching_rect": [
						615.5,
						420,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-thresh-7",
					"maxclass": "newobj",
					"text": "> 0.5",
					"patching_rect": [
						590,
						450,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "onset-sel-7",
					"maxclass": "newobj",
					"text": "sel 1",
					"patching_rect": [
						590,
						475,
						40.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						""
					]
				}
			},
			{
				"box": {
					"id": "label-8",
					"maxclass": "comment",
					"text": "ch9",
					"patching_rect": [
						670,
						235,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rms-slider-8",
					"maxclass": "slider",
					"patching_rect": [
						696.5,
						257,
						22.0,
						130.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"size": 128,
					"floatoutput": 0,
					"min": 0.0,
					"mult": 300.0
				}
			},
			{
				"box": {
					"id": "centroid-8",
					"maxclass": "number",
					"patching_rect": [
						670,
						393,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-8",
					"maxclass": "button",
					"patching_rect": [
						695.5,
						420,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-thresh-8",
					"maxclass": "newobj",
					"text": "> 0.5",
					"patching_rect": [
						670,
						450,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "onset-sel-8",
					"maxclass": "newobj",
					"text": "sel 1",
					"patching_rect": [
						670,
						475,
						40.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						""
					]
				}
			},
			{
				"box": {
					"id": "label-9",
					"maxclass": "comment",
					"text": "ch10",
					"patching_rect": [
						750,
						235,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rms-slider-9",
					"maxclass": "slider",
					"patching_rect": [
						776.5,
						257,
						22.0,
						130.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"size": 128,
					"floatoutput": 0,
					"min": 0.0,
					"mult": 300.0
				}
			},
			{
				"box": {
					"id": "centroid-9",
					"maxclass": "number",
					"patching_rect": [
						750,
						393,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-9",
					"maxclass": "button",
					"patching_rect": [
						775.5,
						420,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-thresh-9",
					"maxclass": "newobj",
					"text": "> 0.5",
					"patching_rect": [
						750,
						450,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "onset-sel-9",
					"maxclass": "newobj",
					"text": "sel 1",
					"patching_rect": [
						750,
						475,
						40.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						""
					]
				}
			},
			{
				"box": {
					"id": "label-10",
					"maxclass": "comment",
					"text": "ch11",
					"patching_rect": [
						830,
						235,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rms-slider-10",
					"maxclass": "slider",
					"patching_rect": [
						856.5,
						257,
						22.0,
						130.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"size": 128,
					"floatoutput": 0,
					"min": 0.0,
					"mult": 300.0
				}
			},
			{
				"box": {
					"id": "centroid-10",
					"maxclass": "number",
					"patching_rect": [
						830,
						393,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-10",
					"maxclass": "button",
					"patching_rect": [
						855.5,
						420,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-thresh-10",
					"maxclass": "newobj",
					"text": "> 0.5",
					"patching_rect": [
						830,
						450,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "onset-sel-10",
					"maxclass": "newobj",
					"text": "sel 1",
					"patching_rect": [
						830,
						475,
						40.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						""
					]
				}
			},
			{
				"box": {
					"id": "label-11",
					"maxclass": "comment",
					"text": "ch12",
					"patching_rect": [
						910,
						235,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rms-slider-11",
					"maxclass": "slider",
					"patching_rect": [
						936.5,
						257,
						22.0,
						130.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"size": 128,
					"floatoutput": 0,
					"min": 0.0,
					"mult": 300.0
				}
			},
			{
				"box": {
					"id": "centroid-11",
					"maxclass": "number",
					"patching_rect": [
						910,
						393,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-11",
					"maxclass": "button",
					"patching_rect": [
						935.5,
						420,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-thresh-11",
					"maxclass": "newobj",
					"text": "> 0.5",
					"patching_rect": [
						910,
						450,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "onset-sel-11",
					"maxclass": "newobj",
					"text": "sel 1",
					"patching_rect": [
						910,
						475,
						40.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						""
					]
				}
			},
			{
				"box": {
					"id": "label-12",
					"maxclass": "comment",
					"text": "ch13",
					"patching_rect": [
						990,
						235,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rms-slider-12",
					"maxclass": "slider",
					"patching_rect": [
						1016.5,
						257,
						22.0,
						130.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"size": 128,
					"floatoutput": 0,
					"min": 0.0,
					"mult": 300.0
				}
			},
			{
				"box": {
					"id": "centroid-12",
					"maxclass": "number",
					"patching_rect": [
						990,
						393,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-12",
					"maxclass": "button",
					"patching_rect": [
						1015.5,
						420,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-thresh-12",
					"maxclass": "newobj",
					"text": "> 0.5",
					"patching_rect": [
						990,
						450,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "onset-sel-12",
					"maxclass": "newobj",
					"text": "sel 1",
					"patching_rect": [
						990,
						475,
						40.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						""
					]
				}
			},
			{
				"box": {
					"id": "label-13",
					"maxclass": "comment",
					"text": "ch14",
					"patching_rect": [
						1070,
						235,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rms-slider-13",
					"maxclass": "slider",
					"patching_rect": [
						1096.5,
						257,
						22.0,
						130.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"size": 128,
					"floatoutput": 0,
					"min": 0.0,
					"mult": 300.0
				}
			},
			{
				"box": {
					"id": "centroid-13",
					"maxclass": "number",
					"patching_rect": [
						1070,
						393,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-13",
					"maxclass": "button",
					"patching_rect": [
						1095.5,
						420,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "onset-thresh-13",
					"maxclass": "newobj",
					"text": "> 0.5",
					"patching_rect": [
						1070,
						450,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "onset-sel-13",
					"maxclass": "newobj",
					"text": "sel 1",
					"patching_rect": [
						1070,
						475,
						40.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"bang",
						""
					]
				}
			},
			{
				"box": {
					"id": "hdr-cv",
					"maxclass": "comment",
					"text": "\u25c6 CV  smoothed DC value \u00b7 rate of change",
					"patching_rect": [
						30.0,
						503,
						540.0,
						20.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rt-cv",
					"maxclass": "newobj",
					"text": "route 1 2 3 4 5 6 7 8 9 10 11 12 13 14",
					"patching_rect": [
						30,
						525,
						1120,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 15,
					"outlettype": [
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "rt-cv-rate",
					"maxclass": "newobj",
					"text": "route 1 2 3 4 5 6 7 8 9 10 11 12 13 14",
					"patching_rect": [
						30,
						553,
						1120,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 15,
					"outlettype": [
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "cv-label-0",
					"maxclass": "comment",
					"text": "ch1",
					"patching_rect": [
						30,
						585,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "cv-val-0",
					"maxclass": "flonum",
					"patching_rect": [
						30,
						607,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-rate-0",
					"maxclass": "flonum",
					"patching_rect": [
						30,
						633,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-label-1",
					"maxclass": "comment",
					"text": "ch2",
					"patching_rect": [
						110,
						585,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "cv-val-1",
					"maxclass": "flonum",
					"patching_rect": [
						110,
						607,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-rate-1",
					"maxclass": "flonum",
					"patching_rect": [
						110,
						633,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-label-2",
					"maxclass": "comment",
					"text": "ch3",
					"patching_rect": [
						190,
						585,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "cv-val-2",
					"maxclass": "flonum",
					"patching_rect": [
						190,
						607,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-rate-2",
					"maxclass": "flonum",
					"patching_rect": [
						190,
						633,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-label-3",
					"maxclass": "comment",
					"text": "ch4",
					"patching_rect": [
						270,
						585,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "cv-val-3",
					"maxclass": "flonum",
					"patching_rect": [
						270,
						607,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-rate-3",
					"maxclass": "flonum",
					"patching_rect": [
						270,
						633,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-label-4",
					"maxclass": "comment",
					"text": "ch5",
					"patching_rect": [
						350,
						585,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "cv-val-4",
					"maxclass": "flonum",
					"patching_rect": [
						350,
						607,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-rate-4",
					"maxclass": "flonum",
					"patching_rect": [
						350,
						633,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-label-5",
					"maxclass": "comment",
					"text": "ch6",
					"patching_rect": [
						430,
						585,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "cv-val-5",
					"maxclass": "flonum",
					"patching_rect": [
						430,
						607,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-rate-5",
					"maxclass": "flonum",
					"patching_rect": [
						430,
						633,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-label-6",
					"maxclass": "comment",
					"text": "ch7",
					"patching_rect": [
						510,
						585,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "cv-val-6",
					"maxclass": "flonum",
					"patching_rect": [
						510,
						607,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-rate-6",
					"maxclass": "flonum",
					"patching_rect": [
						510,
						633,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-label-7",
					"maxclass": "comment",
					"text": "ch8",
					"patching_rect": [
						590,
						585,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "cv-val-7",
					"maxclass": "flonum",
					"patching_rect": [
						590,
						607,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-rate-7",
					"maxclass": "flonum",
					"patching_rect": [
						590,
						633,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-label-8",
					"maxclass": "comment",
					"text": "ch9",
					"patching_rect": [
						670,
						585,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "cv-val-8",
					"maxclass": "flonum",
					"patching_rect": [
						670,
						607,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-rate-8",
					"maxclass": "flonum",
					"patching_rect": [
						670,
						633,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-label-9",
					"maxclass": "comment",
					"text": "ch10",
					"patching_rect": [
						750,
						585,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "cv-val-9",
					"maxclass": "flonum",
					"patching_rect": [
						750,
						607,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-rate-9",
					"maxclass": "flonum",
					"patching_rect": [
						750,
						633,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-label-10",
					"maxclass": "comment",
					"text": "ch11",
					"patching_rect": [
						830,
						585,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "cv-val-10",
					"maxclass": "flonum",
					"patching_rect": [
						830,
						607,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-rate-10",
					"maxclass": "flonum",
					"patching_rect": [
						830,
						633,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-label-11",
					"maxclass": "comment",
					"text": "ch12",
					"patching_rect": [
						910,
						585,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "cv-val-11",
					"maxclass": "flonum",
					"patching_rect": [
						910,
						607,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-rate-11",
					"maxclass": "flonum",
					"patching_rect": [
						910,
						633,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-label-12",
					"maxclass": "comment",
					"text": "ch13",
					"patching_rect": [
						990,
						585,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "cv-val-12",
					"maxclass": "flonum",
					"patching_rect": [
						990,
						607,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-rate-12",
					"maxclass": "flonum",
					"patching_rect": [
						990,
						633,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-label-13",
					"maxclass": "comment",
					"text": "ch14",
					"patching_rect": [
						1070,
						585,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "cv-val-13",
					"maxclass": "flonum",
					"patching_rect": [
						1070,
						607,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "cv-rate-13",
					"maxclass": "flonum",
					"patching_rect": [
						1070,
						633,
						75,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "hdr-gate",
					"maxclass": "comment",
					"text": "\u25c6 GATE  state toggle \u00b7 edge bang (any rising/falling edge)",
					"patching_rect": [
						30.0,
						663,
						540.0,
						20.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "rt-gate",
					"maxclass": "newobj",
					"text": "route 1 2 3 4 5 6 7 8 9 10 11 12 13 14",
					"patching_rect": [
						30,
						685,
						1120,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 15,
					"outlettype": [
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "rt-gate-event",
					"maxclass": "newobj",
					"text": "route 1 2 3 4 5 6 7 8 9 10 11 12 13 14",
					"patching_rect": [
						30,
						713,
						1120,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 15,
					"outlettype": [
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "gate-label-0",
					"maxclass": "comment",
					"text": "ch1",
					"patching_rect": [
						30,
						745,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "gate-toggle-0",
					"maxclass": "toggle",
					"patching_rect": [
						53.5,
						767,
						28.0,
						28.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"parameter_enable": 0
				}
			},
			{
				"box": {
					"id": "gate-edge-0",
					"maxclass": "button",
					"patching_rect": [
						55.5,
						801,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "gate-label-1",
					"maxclass": "comment",
					"text": "ch2",
					"patching_rect": [
						110,
						745,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "gate-toggle-1",
					"maxclass": "toggle",
					"patching_rect": [
						133.5,
						767,
						28.0,
						28.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"parameter_enable": 0
				}
			},
			{
				"box": {
					"id": "gate-edge-1",
					"maxclass": "button",
					"patching_rect": [
						135.5,
						801,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "gate-label-2",
					"maxclass": "comment",
					"text": "ch3",
					"patching_rect": [
						190,
						745,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "gate-toggle-2",
					"maxclass": "toggle",
					"patching_rect": [
						213.5,
						767,
						28.0,
						28.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"parameter_enable": 0
				}
			},
			{
				"box": {
					"id": "gate-edge-2",
					"maxclass": "button",
					"patching_rect": [
						215.5,
						801,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "gate-label-3",
					"maxclass": "comment",
					"text": "ch4",
					"patching_rect": [
						270,
						745,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "gate-toggle-3",
					"maxclass": "toggle",
					"patching_rect": [
						293.5,
						767,
						28.0,
						28.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"parameter_enable": 0
				}
			},
			{
				"box": {
					"id": "gate-edge-3",
					"maxclass": "button",
					"patching_rect": [
						295.5,
						801,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "gate-label-4",
					"maxclass": "comment",
					"text": "ch5",
					"patching_rect": [
						350,
						745,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "gate-toggle-4",
					"maxclass": "toggle",
					"patching_rect": [
						373.5,
						767,
						28.0,
						28.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"parameter_enable": 0
				}
			},
			{
				"box": {
					"id": "gate-edge-4",
					"maxclass": "button",
					"patching_rect": [
						375.5,
						801,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "gate-label-5",
					"maxclass": "comment",
					"text": "ch6",
					"patching_rect": [
						430,
						745,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "gate-toggle-5",
					"maxclass": "toggle",
					"patching_rect": [
						453.5,
						767,
						28.0,
						28.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"parameter_enable": 0
				}
			},
			{
				"box": {
					"id": "gate-edge-5",
					"maxclass": "button",
					"patching_rect": [
						455.5,
						801,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "gate-label-6",
					"maxclass": "comment",
					"text": "ch7",
					"patching_rect": [
						510,
						745,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "gate-toggle-6",
					"maxclass": "toggle",
					"patching_rect": [
						533.5,
						767,
						28.0,
						28.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"parameter_enable": 0
				}
			},
			{
				"box": {
					"id": "gate-edge-6",
					"maxclass": "button",
					"patching_rect": [
						535.5,
						801,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "gate-label-7",
					"maxclass": "comment",
					"text": "ch8",
					"patching_rect": [
						590,
						745,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "gate-toggle-7",
					"maxclass": "toggle",
					"patching_rect": [
						613.5,
						767,
						28.0,
						28.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"parameter_enable": 0
				}
			},
			{
				"box": {
					"id": "gate-edge-7",
					"maxclass": "button",
					"patching_rect": [
						615.5,
						801,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "gate-label-8",
					"maxclass": "comment",
					"text": "ch9",
					"patching_rect": [
						670,
						745,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "gate-toggle-8",
					"maxclass": "toggle",
					"patching_rect": [
						693.5,
						767,
						28.0,
						28.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"parameter_enable": 0
				}
			},
			{
				"box": {
					"id": "gate-edge-8",
					"maxclass": "button",
					"patching_rect": [
						695.5,
						801,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "gate-label-9",
					"maxclass": "comment",
					"text": "ch10",
					"patching_rect": [
						750,
						745,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "gate-toggle-9",
					"maxclass": "toggle",
					"patching_rect": [
						773.5,
						767,
						28.0,
						28.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"parameter_enable": 0
				}
			},
			{
				"box": {
					"id": "gate-edge-9",
					"maxclass": "button",
					"patching_rect": [
						775.5,
						801,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "gate-label-10",
					"maxclass": "comment",
					"text": "ch11",
					"patching_rect": [
						830,
						745,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "gate-toggle-10",
					"maxclass": "toggle",
					"patching_rect": [
						853.5,
						767,
						28.0,
						28.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"parameter_enable": 0
				}
			},
			{
				"box": {
					"id": "gate-edge-10",
					"maxclass": "button",
					"patching_rect": [
						855.5,
						801,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "gate-label-11",
					"maxclass": "comment",
					"text": "ch12",
					"patching_rect": [
						910,
						745,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "gate-toggle-11",
					"maxclass": "toggle",
					"patching_rect": [
						933.5,
						767,
						28.0,
						28.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"parameter_enable": 0
				}
			},
			{
				"box": {
					"id": "gate-edge-11",
					"maxclass": "button",
					"patching_rect": [
						935.5,
						801,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "gate-label-12",
					"maxclass": "comment",
					"text": "ch13",
					"patching_rect": [
						990,
						745,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "gate-toggle-12",
					"maxclass": "toggle",
					"patching_rect": [
						1013.5,
						767,
						28.0,
						28.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"parameter_enable": 0
				}
			},
			{
				"box": {
					"id": "gate-edge-12",
					"maxclass": "button",
					"patching_rect": [
						1015.5,
						801,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "gate-label-13",
					"maxclass": "comment",
					"text": "ch14",
					"patching_rect": [
						1070,
						745,
						75,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "gate-toggle-13",
					"maxclass": "toggle",
					"patching_rect": [
						1093.5,
						767,
						28.0,
						28.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					],
					"parameter_enable": 0
				}
			},
			{
				"box": {
					"id": "gate-edge-13",
					"maxclass": "button",
					"patching_rect": [
						1095.5,
						801,
						24.0,
						24.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"bang"
					]
				}
			},
			{
				"box": {
					"id": "hdr-spec",
					"maxclass": "comment",
					"text": "\u25c6 SPECTRUM  pick a channel (only audio-role channels emit) \u00b7 32 log-spaced bins \u00b7 ~30Hz",
					"patching_rect": [
						30.0,
						833,
						700.0,
						20.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "spec-menu",
					"maxclass": "umenu",
					"patching_rect": [
						30.0,
						855,
						100.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 3,
					"outlettype": [
						"int",
						"",
						""
					],
					"items": [
						"ch1",
						"ch2",
						"ch3",
						"ch4",
						"ch5",
						"ch6",
						"ch7",
						"ch8",
						"ch9",
						"ch10",
						"ch11",
						"ch12",
						"ch13",
						"ch14"
					]
				}
			},
			{
				"box": {
					"id": "spec-menu-label",
					"maxclass": "comment",
					"text": "\u2190 select channel  (sent to v8 inlet 1; JS converts 0-based umenu int to 1-based ch)",
					"patching_rect": [
						140.0,
						857,
						600.0,
						18.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "spec-multi",
					"maxclass": "multislider",
					"patching_rect": [
						30.0,
						890,
						1080.0,
						120.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					],
					"size": 32,
					"contdata": 1,
					"setminmax": [
						0.0,
						1.0
					],
					"slidercolor": [
						0.984,
						0.949,
						0.831,
						1.0
					],
					"bgcolor": [
						0.094,
						0.094,
						0.094,
						1.0
					],
					"setstyle": 0,
					"candicable": 0
				}
			},
			{
				"box": {
					"id": "hdr-clap",
					"maxclass": "comment",
					"text": "\u25c6 CLAP  512-D audio embedding (slow tier ~1Hz, only when --clap is on)",
					"patching_rect": [
						30.0,
						1008,
						700.0,
						20.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "clap-multi",
					"maxclass": "multislider",
					"patching_rect": [
						30.0,
						1030,
						1080.0,
						80.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						"bang"
					],
					"size": 512,
					"contdata": 1,
					"setminmax": [
						-1.0,
						1.0
					],
					"slidercolor": [
						0.65,
						0.85,
						0.95,
						1.0
					],
					"bgcolor": [
						0.094,
						0.094,
						0.094,
						1.0
					],
					"setstyle": 0,
					"candicable": 0
				}
			},
			{
				"box": {
					"id": "clap-zl",
					"maxclass": "newobj",
					"text": "zl group 512",
					"patching_rect": [
						30.0,
						1120,
						130.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 2,
					"outlettype": [
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "footer",
					"maxclass": "comment",
					"text": "Forward to Unreal:  add a [udpsend <unreal-host> <unreal-port>] and tap any of\nthe [route 1..14] outlets above (or the v8 category outlets directly).\n/synapse/cv/N for slow control, /gate/N for triggers, /spectrum/N for the bin lists.\nFull schema: docs/OSC_SCHEMA.md.",
					"patching_rect": [
						30.0,
						1160,
						1080.0,
						70.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			}
		],
		"lines": [
			{
				"patchline": {
					"source": [
						"udpreceive",
						0
					],
					"destination": [
						"v8-router",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"v8-router",
						8
					],
					"destination": [
						"status-block",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"v8-router",
						8
					],
					"destination": [
						"status-tick",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"status-tick",
						0
					],
					"destination": [
						"status-counter",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"status-counter",
						0
					],
					"destination": [
						"status-count",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"v8-router",
						0
					],
					"destination": [
						"rt-rms",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"v8-router",
						1
					],
					"destination": [
						"rt-centroid",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"v8-router",
						2
					],
					"destination": [
						"rt-onset",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-rms",
						0
					],
					"destination": [
						"rms-slider-0",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-centroid",
						0
					],
					"destination": [
						"centroid-0",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-onset",
						0
					],
					"destination": [
						"onset-thresh-0",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-thresh-0",
						0
					],
					"destination": [
						"onset-sel-0",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-sel-0",
						0
					],
					"destination": [
						"onset-0",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-rms",
						1
					],
					"destination": [
						"rms-slider-1",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-centroid",
						1
					],
					"destination": [
						"centroid-1",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-onset",
						1
					],
					"destination": [
						"onset-thresh-1",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-thresh-1",
						0
					],
					"destination": [
						"onset-sel-1",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-sel-1",
						0
					],
					"destination": [
						"onset-1",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-rms",
						2
					],
					"destination": [
						"rms-slider-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-centroid",
						2
					],
					"destination": [
						"centroid-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-onset",
						2
					],
					"destination": [
						"onset-thresh-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-thresh-2",
						0
					],
					"destination": [
						"onset-sel-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-sel-2",
						0
					],
					"destination": [
						"onset-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-rms",
						3
					],
					"destination": [
						"rms-slider-3",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-centroid",
						3
					],
					"destination": [
						"centroid-3",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-onset",
						3
					],
					"destination": [
						"onset-thresh-3",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-thresh-3",
						0
					],
					"destination": [
						"onset-sel-3",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-sel-3",
						0
					],
					"destination": [
						"onset-3",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-rms",
						4
					],
					"destination": [
						"rms-slider-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-centroid",
						4
					],
					"destination": [
						"centroid-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-onset",
						4
					],
					"destination": [
						"onset-thresh-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-thresh-4",
						0
					],
					"destination": [
						"onset-sel-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-sel-4",
						0
					],
					"destination": [
						"onset-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-rms",
						5
					],
					"destination": [
						"rms-slider-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-centroid",
						5
					],
					"destination": [
						"centroid-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-onset",
						5
					],
					"destination": [
						"onset-thresh-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-thresh-5",
						0
					],
					"destination": [
						"onset-sel-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-sel-5",
						0
					],
					"destination": [
						"onset-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-rms",
						6
					],
					"destination": [
						"rms-slider-6",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-centroid",
						6
					],
					"destination": [
						"centroid-6",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-onset",
						6
					],
					"destination": [
						"onset-thresh-6",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-thresh-6",
						0
					],
					"destination": [
						"onset-sel-6",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-sel-6",
						0
					],
					"destination": [
						"onset-6",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-rms",
						7
					],
					"destination": [
						"rms-slider-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-centroid",
						7
					],
					"destination": [
						"centroid-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-onset",
						7
					],
					"destination": [
						"onset-thresh-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-thresh-7",
						0
					],
					"destination": [
						"onset-sel-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-sel-7",
						0
					],
					"destination": [
						"onset-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-rms",
						8
					],
					"destination": [
						"rms-slider-8",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-centroid",
						8
					],
					"destination": [
						"centroid-8",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-onset",
						8
					],
					"destination": [
						"onset-thresh-8",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-thresh-8",
						0
					],
					"destination": [
						"onset-sel-8",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-sel-8",
						0
					],
					"destination": [
						"onset-8",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-rms",
						9
					],
					"destination": [
						"rms-slider-9",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-centroid",
						9
					],
					"destination": [
						"centroid-9",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-onset",
						9
					],
					"destination": [
						"onset-thresh-9",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-thresh-9",
						0
					],
					"destination": [
						"onset-sel-9",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-sel-9",
						0
					],
					"destination": [
						"onset-9",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-rms",
						10
					],
					"destination": [
						"rms-slider-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-centroid",
						10
					],
					"destination": [
						"centroid-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-onset",
						10
					],
					"destination": [
						"onset-thresh-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-thresh-10",
						0
					],
					"destination": [
						"onset-sel-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-sel-10",
						0
					],
					"destination": [
						"onset-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-rms",
						11
					],
					"destination": [
						"rms-slider-11",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-centroid",
						11
					],
					"destination": [
						"centroid-11",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-onset",
						11
					],
					"destination": [
						"onset-thresh-11",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-thresh-11",
						0
					],
					"destination": [
						"onset-sel-11",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-sel-11",
						0
					],
					"destination": [
						"onset-11",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-rms",
						12
					],
					"destination": [
						"rms-slider-12",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-centroid",
						12
					],
					"destination": [
						"centroid-12",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-onset",
						12
					],
					"destination": [
						"onset-thresh-12",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-thresh-12",
						0
					],
					"destination": [
						"onset-sel-12",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-sel-12",
						0
					],
					"destination": [
						"onset-12",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-rms",
						13
					],
					"destination": [
						"rms-slider-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-centroid",
						13
					],
					"destination": [
						"centroid-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-onset",
						13
					],
					"destination": [
						"onset-thresh-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-thresh-13",
						0
					],
					"destination": [
						"onset-sel-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"onset-sel-13",
						0
					],
					"destination": [
						"onset-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"v8-router",
						3
					],
					"destination": [
						"rt-cv",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"v8-router",
						4
					],
					"destination": [
						"rt-cv-rate",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv",
						0
					],
					"destination": [
						"cv-val-0",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv-rate",
						0
					],
					"destination": [
						"cv-rate-0",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv",
						1
					],
					"destination": [
						"cv-val-1",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv-rate",
						1
					],
					"destination": [
						"cv-rate-1",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv",
						2
					],
					"destination": [
						"cv-val-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv-rate",
						2
					],
					"destination": [
						"cv-rate-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv",
						3
					],
					"destination": [
						"cv-val-3",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv-rate",
						3
					],
					"destination": [
						"cv-rate-3",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv",
						4
					],
					"destination": [
						"cv-val-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv-rate",
						4
					],
					"destination": [
						"cv-rate-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv",
						5
					],
					"destination": [
						"cv-val-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv-rate",
						5
					],
					"destination": [
						"cv-rate-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv",
						6
					],
					"destination": [
						"cv-val-6",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv-rate",
						6
					],
					"destination": [
						"cv-rate-6",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv",
						7
					],
					"destination": [
						"cv-val-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv-rate",
						7
					],
					"destination": [
						"cv-rate-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv",
						8
					],
					"destination": [
						"cv-val-8",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv-rate",
						8
					],
					"destination": [
						"cv-rate-8",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv",
						9
					],
					"destination": [
						"cv-val-9",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv-rate",
						9
					],
					"destination": [
						"cv-rate-9",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv",
						10
					],
					"destination": [
						"cv-val-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv-rate",
						10
					],
					"destination": [
						"cv-rate-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv",
						11
					],
					"destination": [
						"cv-val-11",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv-rate",
						11
					],
					"destination": [
						"cv-rate-11",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv",
						12
					],
					"destination": [
						"cv-val-12",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv-rate",
						12
					],
					"destination": [
						"cv-rate-12",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv",
						13
					],
					"destination": [
						"cv-val-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-cv-rate",
						13
					],
					"destination": [
						"cv-rate-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"v8-router",
						5
					],
					"destination": [
						"rt-gate",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"v8-router",
						6
					],
					"destination": [
						"rt-gate-event",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate",
						0
					],
					"destination": [
						"gate-toggle-0",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate-event",
						0
					],
					"destination": [
						"gate-edge-0",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate",
						1
					],
					"destination": [
						"gate-toggle-1",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate-event",
						1
					],
					"destination": [
						"gate-edge-1",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate",
						2
					],
					"destination": [
						"gate-toggle-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate-event",
						2
					],
					"destination": [
						"gate-edge-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate",
						3
					],
					"destination": [
						"gate-toggle-3",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate-event",
						3
					],
					"destination": [
						"gate-edge-3",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate",
						4
					],
					"destination": [
						"gate-toggle-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate-event",
						4
					],
					"destination": [
						"gate-edge-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate",
						5
					],
					"destination": [
						"gate-toggle-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate-event",
						5
					],
					"destination": [
						"gate-edge-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate",
						6
					],
					"destination": [
						"gate-toggle-6",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate-event",
						6
					],
					"destination": [
						"gate-edge-6",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate",
						7
					],
					"destination": [
						"gate-toggle-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate-event",
						7
					],
					"destination": [
						"gate-edge-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate",
						8
					],
					"destination": [
						"gate-toggle-8",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate-event",
						8
					],
					"destination": [
						"gate-edge-8",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate",
						9
					],
					"destination": [
						"gate-toggle-9",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate-event",
						9
					],
					"destination": [
						"gate-edge-9",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate",
						10
					],
					"destination": [
						"gate-toggle-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate-event",
						10
					],
					"destination": [
						"gate-edge-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate",
						11
					],
					"destination": [
						"gate-toggle-11",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate-event",
						11
					],
					"destination": [
						"gate-edge-11",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate",
						12
					],
					"destination": [
						"gate-toggle-12",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate-event",
						12
					],
					"destination": [
						"gate-edge-12",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate",
						13
					],
					"destination": [
						"gate-toggle-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-gate-event",
						13
					],
					"destination": [
						"gate-edge-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-menu",
						0
					],
					"destination": [
						"v8-router",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"v8-router",
						7
					],
					"destination": [
						"spec-multi",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"v8-router",
						9
					],
					"destination": [
						"clap-zl",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"clap-zl",
						0
					],
					"destination": [
						"clap-multi",
						0
					]
				}
			}
		]
	}
}
