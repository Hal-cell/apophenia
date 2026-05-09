{
	"patcher" :     {
		"fileversion" : 1,
		"appversion" :         {
			"major" : 8,
			"minor" : 6,
			"revision" : 0,
			"architecture" : "x64",
			"modernui" : 1
		},
		"classnamespace" : "box",
		"rect" : [ 80.0, 80.0, 1100.0, 720.0 ],
		"bglocked" : 0,
		"openinpresentation" : 0,
		"default_fontsize" : 12.0,
		"default_fontface" : 0,
		"default_fontname" : "Arial",
		"gridonopen" : 1,
		"gridsize" : [ 15.0, 15.0 ],
		"gridsnaponopen" : 1,
		"objectsnaponopen" : 1,
		"statusbarvisible" : 2,
		"toolbarvisible" : 1,
		"lefttoolbarpinned" : 0,
		"toptoolbarpinned" : 0,
		"righttoolbarpinned" : 0,
		"bottomtoolbarpinned" : 0,
		"toolbars_unpinned_last_save" : 0,
		"tallnewobj" : 0,
		"boxanimatetime" : 200,
		"enablehscroll" : 1,
		"enablevscroll" : 1,
		"devicewidth" : 0.0,
		"description" : "synapse starter — receives synapse OSC streams on UDP 9000",
		"digest" : "",
		"tags" : "",
		"style" : "",
		"subpatcher_template" : "",
		"assistshowspatchername" : 0,
		"boxes" : [
			{ "box" :  {
				"id" : "obj-title",
				"maxclass" : "comment",
				"text" : "synapse → MaxMSP starter\n\nReceives the OSC streams documented in docs/OSC_SCHEMA.md.\nDefault: localhost UDP 9000. Change the [udpreceive] arg if synapse runs elsewhere.",
				"patching_rect" : [ 30.0, 20.0, 540.0, 80.0 ],
				"fontsize" : 13.0,
				"numinlets" : 1,
				"numoutlets" : 0
			} },
			{ "box" :  {
				"id" : "obj-udpreceive",
				"maxclass" : "newobj",
				"text" : "udpreceive 9000",
				"patching_rect" : [ 30.0, 110.0, 130.0, 22.0 ],
				"numinlets" : 1,
				"numoutlets" : 1,
				"outlettype" : [ "" ]
			} },
			{ "box" :  {
				"id" : "obj-oscparse",
				"maxclass" : "newobj",
				"text" : "oscparse",
				"patching_rect" : [ 30.0, 145.0, 80.0, 22.0 ],
				"numinlets" : 1,
				"numoutlets" : 1,
				"outlettype" : [ "" ]
			} },
			{ "box" :  {
				"id" : "obj-route-synapse",
				"maxclass" : "newobj",
				"text" : "route /synapse",
				"patching_rect" : [ 30.0, 180.0, 130.0, 22.0 ],
				"numinlets" : 1,
				"numoutlets" : 2,
				"outlettype" : [ "", "" ]
			} },
			{ "box" :  {
				"id" : "obj-route-categories",
				"maxclass" : "newobj",
				"text" : "route cv gate gate_event rms onset centroid peak spectrum block clap",
				"patching_rect" : [ 30.0, 215.0, 540.0, 22.0 ],
				"numinlets" : 1,
				"numoutlets" : 11,
				"outlettype" : [ "", "", "", "", "", "", "", "", "", "", "" ]
			} },
			{ "box" :  {
				"id" : "obj-comment-cv",
				"maxclass" : "comment",
				"text" : "/cv/N float — smoothed DC. Only sent when changed (cv_eps).",
				"patching_rect" : [ 30.0, 260.0, 360.0, 20.0 ]
			} },
			{ "box" :  {
				"id" : "obj-route-cv-channels",
				"maxclass" : "newobj",
				"text" : "route /1 /2 /3 /4 /5 /6 /7 /8 /9 /10 /11 /12 /13 /14",
				"patching_rect" : [ 30.0, 285.0, 460.0, 22.0 ],
				"numinlets" : 1,
				"numoutlets" : 15,
				"outlettype" : [ "", "", "", "", "", "", "", "", "", "", "", "", "", "", "" ]
			} },
			{ "box" :  {
				"id" : "obj-cv1-num",
				"maxclass" : "flonum",
				"text" : "0.",
				"patching_rect" : [ 30.0, 320.0, 60.0, 22.0 ],
				"numinlets" : 1,
				"numoutlets" : 2,
				"outlettype" : [ "", "bang" ]
			} },
			{ "box" :  {
				"id" : "obj-cv1-label",
				"maxclass" : "comment",
				"text" : "ch1 CV",
				"patching_rect" : [ 95.0, 322.0, 60.0, 20.0 ]
			} },
			{ "box" :  {
				"id" : "obj-comment-gate",
				"maxclass" : "comment",
				"text" : "/gate/N int 0|1 — current state every block. /gate_event/N \"rising\"|\"falling\" — edge events.",
				"patching_rect" : [ 30.0, 365.0, 480.0, 20.0 ]
			} },
			{ "box" :  {
				"id" : "obj-route-gate-channels",
				"maxclass" : "newobj",
				"text" : "route /1 /2 /3 /4 /5 /6 /7 /8 /9 /10 /11 /12 /13 /14",
				"patching_rect" : [ 30.0, 390.0, 460.0, 22.0 ],
				"numinlets" : 1,
				"numoutlets" : 15,
				"outlettype" : [ "", "", "", "", "", "", "", "", "", "", "", "", "", "", "" ]
			} },
			{ "box" :  {
				"id" : "obj-gate1-toggle",
				"maxclass" : "toggle",
				"patching_rect" : [ 30.0, 425.0, 24.0, 24.0 ],
				"numinlets" : 1,
				"numoutlets" : 1,
				"outlettype" : [ "int" ],
				"parameter_enable" : 0
			} },
			{ "box" :  {
				"id" : "obj-gate1-label",
				"maxclass" : "comment",
				"text" : "ch1 gate state",
				"patching_rect" : [ 60.0, 428.0, 110.0, 20.0 ]
			} },
			{ "box" :  {
				"id" : "obj-route-event-channels",
				"maxclass" : "newobj",
				"text" : "route /1 /2 /3 /4 /5 /6 /7 /8 /9 /10 /11 /12 /13 /14",
				"patching_rect" : [ 30.0, 465.0, 460.0, 22.0 ],
				"numinlets" : 1,
				"numoutlets" : 15,
				"outlettype" : [ "", "", "", "", "", "", "", "", "", "", "", "", "", "", "" ]
			} },
			{ "box" :  {
				"id" : "obj-gate1-event-bang",
				"maxclass" : "button",
				"patching_rect" : [ 30.0, 500.0, 24.0, 24.0 ],
				"numinlets" : 1,
				"numoutlets" : 1,
				"outlettype" : [ "bang" ]
			} },
			{ "box" :  {
				"id" : "obj-gate1-event-label",
				"maxclass" : "comment",
				"text" : "ch1 rising-edge bang (any edge → bang; filter for \"rising\" / \"falling\" with [route] if needed)",
				"patching_rect" : [ 60.0, 503.0, 540.0, 20.0 ]
			} },
			{ "box" :  {
				"id" : "obj-comment-spectrum",
				"maxclass" : "comment",
				"text" : "/spectrum/N — 32 log-spaced magnitude bins per audio channel @ ~30Hz. Drives [multislider] directly.",
				"patching_rect" : [ 30.0, 540.0, 600.0, 20.0 ]
			} },
			{ "box" :  {
				"id" : "obj-route-spectrum-channels",
				"maxclass" : "newobj",
				"text" : "route /1 /2 /3 /4 /5 /6 /7 /8 /9 /10 /11 /12 /13 /14",
				"patching_rect" : [ 30.0, 565.0, 460.0, 22.0 ],
				"numinlets" : 1,
				"numoutlets" : 15,
				"outlettype" : [ "", "", "", "", "", "", "", "", "", "", "", "", "", "", "" ]
			} },
			{ "box" :  {
				"id" : "obj-spec1-mslider",
				"maxclass" : "multislider",
				"patching_rect" : [ 30.0, 600.0, 320.0, 80.0 ],
				"numinlets" : 1,
				"numoutlets" : 2,
				"outlettype" : [ "", "bang" ],
				"size" : 32,
				"contdata" : 1,
				"setminmax" : [ 0.0, 1.0 ],
				"slidercolor" : [ 0.984, 0.949, 0.831, 1.0 ],
				"bgcolor" : [ 0.094, 0.094, 0.094, 1.0 ],
				"setstyle" : 0
			} },
			{ "box" :  {
				"id" : "obj-spec1-label",
				"maxclass" : "comment",
				"text" : "ch1 spectrum (32 bins)",
				"patching_rect" : [ 360.0, 625.0, 200.0, 20.0 ]
			} },
			{ "box" :  {
				"id" : "obj-comment-other",
				"maxclass" : "comment",
				"text" : "Other streams (rms, peak, centroid, onset, block, clap) routed but not visualised — extend as needed.",
				"patching_rect" : [ 30.0, 700.0, 700.0, 20.0 ]
			} },
			{ "box" :  {
				"id" : "obj-comment-extend",
				"maxclass" : "comment",
				"text" : "To forward to Unreal: tap any of the routed signals → [udpsend <unreal-host> <unreal-port>] with whatever address pattern Unreal is set up to receive.\n\nFull schema in docs/OSC_SCHEMA.md.",
				"patching_rect" : [ 30.0, 745.0, 800.0, 60.0 ]
			} }
		],
		"lines" : [
			{ "patchline" :  {
				"source" : [ "obj-udpreceive", 0 ],
				"destination" : [ "obj-oscparse", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-oscparse", 0 ],
				"destination" : [ "obj-route-synapse", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-route-synapse", 0 ],
				"destination" : [ "obj-route-categories", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-route-categories", 0 ],
				"destination" : [ "obj-route-cv-channels", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-route-cv-channels", 0 ],
				"destination" : [ "obj-cv1-num", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-route-categories", 1 ],
				"destination" : [ "obj-route-gate-channels", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-route-gate-channels", 0 ],
				"destination" : [ "obj-gate1-toggle", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-route-categories", 2 ],
				"destination" : [ "obj-route-event-channels", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-route-event-channels", 0 ],
				"destination" : [ "obj-gate1-event-bang", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-route-categories", 7 ],
				"destination" : [ "obj-route-spectrum-channels", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-route-spectrum-channels", 0 ],
				"destination" : [ "obj-spec1-mslider", 0 ]
			} }
		]
	}
}
