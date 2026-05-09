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
			1490
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
		"description": "synapse \u2014 comprehensive 14-channel OSC receiver. Reads bundles on UDP 9000, displays RMS / centroid / onset / CV / gate / spectrum / CLAP for every channel.",
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
					"text": "synapse \u00b7 MaxMSP receiver\n14ch audio analyser \u2192 OSC bundles on UDP 9000",
					"patching_rect": [
						30.0,
						15.0,
						480.0,
						40.0
					],
					"fontsize": 14.0,
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
						540.0,
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
						670.0,
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
						670.0,
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
						670.0,
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
						770.0,
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
						830.0,
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
					"id": "route-synapse",
					"maxclass": "newobj",
					"text": "route /synapse",
					"patching_rect": [
						30.0,
						105.0,
						130.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 2,
					"outlettype": [
						"",
						""
					]
				}
			},
			{
				"box": {
					"id": "route-cat",
					"maxclass": "newobj",
					"text": "route cv cv_rate gate gate_event rms peak centroid onset spectrum block clap",
					"patching_rect": [
						30.0,
						135.0,
						660.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 12,
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
						""
					]
				}
			},
			{
				"box": {
					"id": "rt-rms",
					"maxclass": "newobj",
					"text": "route /1 /2 /3 /4 /5 /6 /7 /8 /9 /10 /11 /12 /13 /14",
					"patching_rect": [
						30,
						220,
						460.0,
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
					"text": "route /1 /2 /3 /4 /5 /6 /7 /8 /9 /10 /11 /12 /13 /14",
					"patching_rect": [
						30,
						250,
						460.0,
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
					"text": "route /1 /2 /3 /4 /5 /6 /7 /8 /9 /10 /11 /12 /13 /14",
					"patching_rect": [
						30,
						280,
						460.0,
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
					"id": "rt-cv",
					"maxclass": "newobj",
					"text": "route /1 /2 /3 /4 /5 /6 /7 /8 /9 /10 /11 /12 /13 /14",
					"patching_rect": [
						30,
						310,
						460.0,
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
					"text": "route /1 /2 /3 /4 /5 /6 /7 /8 /9 /10 /11 /12 /13 /14",
					"patching_rect": [
						30,
						340,
						460.0,
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
					"id": "rt-gate",
					"maxclass": "newobj",
					"text": "route /1 /2 /3 /4 /5 /6 /7 /8 /9 /10 /11 /12 /13 /14",
					"patching_rect": [
						30,
						370,
						460.0,
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
					"text": "route /1 /2 /3 /4 /5 /6 /7 /8 /9 /10 /11 /12 /13 /14",
					"patching_rect": [
						30,
						400,
						460.0,
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
					"id": "rt-spectrum",
					"maxclass": "newobj",
					"text": "route /1 /2 /3 /4 /5 /6 /7 /8 /9 /10 /11 /12 /13 /14",
					"patching_rect": [
						30,
						430,
						460.0,
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
					"id": "hdr-meter",
					"maxclass": "comment",
					"text": "\u25c6 AUDIO  RMS sliders \u00b7 centroid # \u00b7 onset bang",
					"patching_rect": [
						30.0,
						458,
						540.0,
						20.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "label-0",
					"maxclass": "comment",
					"text": "ch1",
					"patching_rect": [
						30,
						480,
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
						502,
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
						638,
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
						665,
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
						695,
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
						720,
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
						480,
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
						502,
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
						638,
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
						665,
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
						695,
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
						720,
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
						480,
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
						502,
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
						638,
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
						665,
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
						695,
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
						720,
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
						480,
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
						502,
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
						638,
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
						665,
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
						695,
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
						720,
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
						480,
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
						502,
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
						638,
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
						665,
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
						695,
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
						720,
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
						480,
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
						502,
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
						638,
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
						665,
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
						695,
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
						720,
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
						480,
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
						502,
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
						638,
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
						665,
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
						695,
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
						720,
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
						480,
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
						502,
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
						638,
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
						665,
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
						695,
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
						720,
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
						480,
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
						502,
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
						638,
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
						665,
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
						695,
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
						720,
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
						480,
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
						502,
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
						638,
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
						665,
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
						695,
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
						720,
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
						480,
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
						502,
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
						638,
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
						665,
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
						695,
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
						720,
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
						480,
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
						502,
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
						638,
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
						665,
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
						695,
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
						720,
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
						480,
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
						502,
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
						638,
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
						665,
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
						695,
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
						720,
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
						480,
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
						502,
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
						638,
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
						665,
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
						695,
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
						720,
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
						748,
						540.0,
						20.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "cv-label-0",
					"maxclass": "comment",
					"text": "ch1",
					"patching_rect": [
						30,
						770,
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
						792,
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
						818,
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
						770,
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
						792,
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
						818,
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
						770,
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
						792,
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
						818,
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
						770,
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
						792,
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
						818,
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
						770,
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
						792,
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
						818,
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
						770,
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
						792,
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
						818,
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
						770,
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
						792,
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
						818,
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
						770,
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
						792,
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
						818,
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
						770,
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
						792,
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
						818,
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
						770,
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
						792,
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
						818,
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
						770,
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
						792,
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
						818,
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
						770,
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
						792,
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
						818,
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
						770,
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
						792,
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
						818,
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
						770,
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
						792,
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
						818,
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
						848,
						540.0,
						20.0
					],
					"numinlets": 1,
					"numoutlets": 0
				}
			},
			{
				"box": {
					"id": "gate-label-0",
					"maxclass": "comment",
					"text": "ch1",
					"patching_rect": [
						30,
						870,
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
						892,
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
						926,
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
						870,
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
						892,
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
						926,
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
						870,
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
						892,
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
						926,
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
						870,
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
						892,
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
						926,
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
						870,
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
						892,
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
						926,
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
						870,
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
						892,
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
						926,
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
						870,
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
						892,
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
						926,
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
						870,
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
						892,
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
						926,
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
						870,
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
						892,
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
						926,
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
						870,
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
						892,
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
						926,
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
						870,
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
						892,
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
						926,
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
						870,
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
						892,
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
						926,
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
						870,
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
						892,
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
						926,
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
						870,
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
						892,
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
						926,
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
						958,
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
						980,
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
					"text": "\u2190 select channel",
					"patching_rect": [
						140.0,
						982,
						200.0,
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
						1015,
						660.0,
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
					"id": "spec-sel-0",
					"maxclass": "newobj",
					"text": "sel 0",
					"patching_rect": [
						30,
						1145,
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
					"id": "spec-gate-0",
					"maxclass": "newobj",
					"text": "gate",
					"patching_rect": [
						30,
						1195,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "spec-t-0",
					"maxclass": "newobj",
					"text": "t 1",
					"patching_rect": [
						30,
						1170,
						30.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "spec-sel-1",
					"maxclass": "newobj",
					"text": "sel 1",
					"patching_rect": [
						80,
						1170,
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
					"id": "spec-gate-1",
					"maxclass": "newobj",
					"text": "gate",
					"patching_rect": [
						80,
						1220,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "spec-t-1",
					"maxclass": "newobj",
					"text": "t 1",
					"patching_rect": [
						80,
						1195,
						30.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "spec-sel-2",
					"maxclass": "newobj",
					"text": "sel 2",
					"patching_rect": [
						130,
						1145,
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
					"id": "spec-gate-2",
					"maxclass": "newobj",
					"text": "gate",
					"patching_rect": [
						130,
						1195,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "spec-t-2",
					"maxclass": "newobj",
					"text": "t 1",
					"patching_rect": [
						130,
						1170,
						30.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "spec-sel-3",
					"maxclass": "newobj",
					"text": "sel 3",
					"patching_rect": [
						180,
						1170,
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
					"id": "spec-gate-3",
					"maxclass": "newobj",
					"text": "gate",
					"patching_rect": [
						180,
						1220,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "spec-t-3",
					"maxclass": "newobj",
					"text": "t 1",
					"patching_rect": [
						180,
						1195,
						30.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "spec-sel-4",
					"maxclass": "newobj",
					"text": "sel 4",
					"patching_rect": [
						230,
						1145,
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
					"id": "spec-gate-4",
					"maxclass": "newobj",
					"text": "gate",
					"patching_rect": [
						230,
						1195,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "spec-t-4",
					"maxclass": "newobj",
					"text": "t 1",
					"patching_rect": [
						230,
						1170,
						30.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "spec-sel-5",
					"maxclass": "newobj",
					"text": "sel 5",
					"patching_rect": [
						280,
						1170,
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
					"id": "spec-gate-5",
					"maxclass": "newobj",
					"text": "gate",
					"patching_rect": [
						280,
						1220,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "spec-t-5",
					"maxclass": "newobj",
					"text": "t 1",
					"patching_rect": [
						280,
						1195,
						30.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "spec-sel-6",
					"maxclass": "newobj",
					"text": "sel 6",
					"patching_rect": [
						330,
						1145,
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
					"id": "spec-gate-6",
					"maxclass": "newobj",
					"text": "gate",
					"patching_rect": [
						330,
						1195,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "spec-t-6",
					"maxclass": "newobj",
					"text": "t 1",
					"patching_rect": [
						330,
						1170,
						30.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "spec-sel-7",
					"maxclass": "newobj",
					"text": "sel 7",
					"patching_rect": [
						380,
						1170,
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
					"id": "spec-gate-7",
					"maxclass": "newobj",
					"text": "gate",
					"patching_rect": [
						380,
						1220,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "spec-t-7",
					"maxclass": "newobj",
					"text": "t 1",
					"patching_rect": [
						380,
						1195,
						30.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "spec-sel-8",
					"maxclass": "newobj",
					"text": "sel 8",
					"patching_rect": [
						430,
						1145,
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
					"id": "spec-gate-8",
					"maxclass": "newobj",
					"text": "gate",
					"patching_rect": [
						430,
						1195,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "spec-t-8",
					"maxclass": "newobj",
					"text": "t 1",
					"patching_rect": [
						430,
						1170,
						30.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "spec-sel-9",
					"maxclass": "newobj",
					"text": "sel 9",
					"patching_rect": [
						480,
						1170,
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
					"id": "spec-gate-9",
					"maxclass": "newobj",
					"text": "gate",
					"patching_rect": [
						480,
						1220,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "spec-t-9",
					"maxclass": "newobj",
					"text": "t 1",
					"patching_rect": [
						480,
						1195,
						30.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "spec-sel-10",
					"maxclass": "newobj",
					"text": "sel 10",
					"patching_rect": [
						530,
						1145,
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
					"id": "spec-gate-10",
					"maxclass": "newobj",
					"text": "gate",
					"patching_rect": [
						530,
						1195,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "spec-t-10",
					"maxclass": "newobj",
					"text": "t 1",
					"patching_rect": [
						530,
						1170,
						30.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "spec-sel-11",
					"maxclass": "newobj",
					"text": "sel 11",
					"patching_rect": [
						580,
						1170,
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
					"id": "spec-gate-11",
					"maxclass": "newobj",
					"text": "gate",
					"patching_rect": [
						580,
						1220,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "spec-t-11",
					"maxclass": "newobj",
					"text": "t 1",
					"patching_rect": [
						580,
						1195,
						30.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "spec-sel-12",
					"maxclass": "newobj",
					"text": "sel 12",
					"patching_rect": [
						630,
						1145,
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
					"id": "spec-gate-12",
					"maxclass": "newobj",
					"text": "gate",
					"patching_rect": [
						630,
						1195,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "spec-t-12",
					"maxclass": "newobj",
					"text": "t 1",
					"patching_rect": [
						630,
						1170,
						30.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "spec-sel-13",
					"maxclass": "newobj",
					"text": "sel 13",
					"patching_rect": [
						680,
						1170,
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
					"id": "spec-gate-13",
					"maxclass": "newobj",
					"text": "gate",
					"patching_rect": [
						680,
						1220,
						50.0,
						22.0
					],
					"numinlets": 2,
					"numoutlets": 1,
					"outlettype": [
						""
					]
				}
			},
			{
				"box": {
					"id": "spec-t-13",
					"maxclass": "newobj",
					"text": "t 1",
					"patching_rect": [
						680,
						1195,
						30.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "spec-closer",
					"maxclass": "newobj",
					"text": "t 0",
					"patching_rect": [
						150.0,
						1145,
						30.0,
						22.0
					],
					"numinlets": 1,
					"numoutlets": 1,
					"outlettype": [
						"int"
					]
				}
			},
			{
				"box": {
					"id": "hdr-clap",
					"maxclass": "comment",
					"text": "\u25c6 CLAP  512-D audio embedding (slow tier ~1Hz, only when --clap is on)",
					"patching_rect": [
						30.0,
						1248,
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
						1270,
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
						1360,
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
					"text": "Forward to Unreal:  add a [udpsend <unreal-host> <unreal-port>] and tap any of\nthe routed signals above. /synapse/cv/N for slow control, /gate/N for triggers,\n/spectrum/N for the bin lists. Full schema: docs/OSC_SCHEMA.md in the repo.",
					"patching_rect": [
						30.0,
						1400,
						1080.0,
						60.0
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
						"route-synapse",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"route-synapse",
						0
					],
					"destination": [
						"route-cat",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"udpreceive",
						0
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
						"route-cat",
						9
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
						"route-cat",
						4
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
						"route-cat",
						6
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
						"route-cat",
						7
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
						"route-cat",
						0
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
						"route-cat",
						1
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
						"route-cat",
						2
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
						"route-cat",
						3
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
						"route-cat",
						8
					],
					"destination": [
						"rt-spectrum",
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
						"spec-sel-0",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-sel-0",
						0
					],
					"destination": [
						"spec-t-0",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-t-0",
						0
					],
					"destination": [
						"spec-gate-0",
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
						"spec-sel-1",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-sel-1",
						0
					],
					"destination": [
						"spec-t-1",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-t-1",
						0
					],
					"destination": [
						"spec-gate-1",
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
						"spec-sel-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-sel-2",
						0
					],
					"destination": [
						"spec-t-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-t-2",
						0
					],
					"destination": [
						"spec-gate-2",
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
						"spec-sel-3",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-sel-3",
						0
					],
					"destination": [
						"spec-t-3",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-t-3",
						0
					],
					"destination": [
						"spec-gate-3",
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
						"spec-sel-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-sel-4",
						0
					],
					"destination": [
						"spec-t-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-t-4",
						0
					],
					"destination": [
						"spec-gate-4",
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
						"spec-sel-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-sel-5",
						0
					],
					"destination": [
						"spec-t-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-t-5",
						0
					],
					"destination": [
						"spec-gate-5",
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
						"spec-sel-6",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-sel-6",
						0
					],
					"destination": [
						"spec-t-6",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-t-6",
						0
					],
					"destination": [
						"spec-gate-6",
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
						"spec-sel-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-sel-7",
						0
					],
					"destination": [
						"spec-t-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-t-7",
						0
					],
					"destination": [
						"spec-gate-7",
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
						"spec-sel-8",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-sel-8",
						0
					],
					"destination": [
						"spec-t-8",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-t-8",
						0
					],
					"destination": [
						"spec-gate-8",
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
						"spec-sel-9",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-sel-9",
						0
					],
					"destination": [
						"spec-t-9",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-t-9",
						0
					],
					"destination": [
						"spec-gate-9",
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
						"spec-sel-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-sel-10",
						0
					],
					"destination": [
						"spec-t-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-t-10",
						0
					],
					"destination": [
						"spec-gate-10",
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
						"spec-sel-11",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-sel-11",
						0
					],
					"destination": [
						"spec-t-11",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-t-11",
						0
					],
					"destination": [
						"spec-gate-11",
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
						"spec-sel-12",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-sel-12",
						0
					],
					"destination": [
						"spec-t-12",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-t-12",
						0
					],
					"destination": [
						"spec-gate-12",
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
						"spec-sel-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-sel-13",
						0
					],
					"destination": [
						"spec-t-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-t-13",
						0
					],
					"destination": [
						"spec-gate-13",
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
						"spec-closer",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-closer",
						0
					],
					"destination": [
						"spec-gate-0",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-closer",
						0
					],
					"destination": [
						"spec-gate-1",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-closer",
						0
					],
					"destination": [
						"spec-gate-2",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-closer",
						0
					],
					"destination": [
						"spec-gate-3",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-closer",
						0
					],
					"destination": [
						"spec-gate-4",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-closer",
						0
					],
					"destination": [
						"spec-gate-5",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-closer",
						0
					],
					"destination": [
						"spec-gate-6",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-closer",
						0
					],
					"destination": [
						"spec-gate-7",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-closer",
						0
					],
					"destination": [
						"spec-gate-8",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-closer",
						0
					],
					"destination": [
						"spec-gate-9",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-closer",
						0
					],
					"destination": [
						"spec-gate-10",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-closer",
						0
					],
					"destination": [
						"spec-gate-11",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-closer",
						0
					],
					"destination": [
						"spec-gate-12",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-closer",
						0
					],
					"destination": [
						"spec-gate-13",
						0
					]
				}
			},
			{
				"patchline": {
					"source": [
						"rt-spectrum",
						0
					],
					"destination": [
						"spec-gate-0",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-gate-0",
						0
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
						"rt-spectrum",
						1
					],
					"destination": [
						"spec-gate-1",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-gate-1",
						0
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
						"rt-spectrum",
						2
					],
					"destination": [
						"spec-gate-2",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-gate-2",
						0
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
						"rt-spectrum",
						3
					],
					"destination": [
						"spec-gate-3",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-gate-3",
						0
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
						"rt-spectrum",
						4
					],
					"destination": [
						"spec-gate-4",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-gate-4",
						0
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
						"rt-spectrum",
						5
					],
					"destination": [
						"spec-gate-5",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-gate-5",
						0
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
						"rt-spectrum",
						6
					],
					"destination": [
						"spec-gate-6",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-gate-6",
						0
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
						"rt-spectrum",
						7
					],
					"destination": [
						"spec-gate-7",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-gate-7",
						0
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
						"rt-spectrum",
						8
					],
					"destination": [
						"spec-gate-8",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-gate-8",
						0
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
						"rt-spectrum",
						9
					],
					"destination": [
						"spec-gate-9",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-gate-9",
						0
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
						"rt-spectrum",
						10
					],
					"destination": [
						"spec-gate-10",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-gate-10",
						0
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
						"rt-spectrum",
						11
					],
					"destination": [
						"spec-gate-11",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-gate-11",
						0
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
						"rt-spectrum",
						12
					],
					"destination": [
						"spec-gate-12",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-gate-12",
						0
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
						"rt-spectrum",
						13
					],
					"destination": [
						"spec-gate-13",
						1
					]
				}
			},
			{
				"patchline": {
					"source": [
						"spec-gate-13",
						0
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
						"route-cat",
						10
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
