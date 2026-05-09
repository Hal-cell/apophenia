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
		"description" : "synapse starter — receives synapse OSC streams on UDP 9000 (ch1 only)",
		"digest" : "",
		"tags" : "",
		"style" : "",
		"subpatcher_template" : "",
		"assistshowspatchername" : 0,
		"boxes" : [
			{ "box" :  {
				"id" : "obj-title",
				"maxclass" : "comment",
				"text" : "synapse → MaxMSP starter (ch1 only)\n\nReceives the OSC streams documented in docs/OSC_SCHEMA.md. Default: localhost UDP 9000.\nThis patch wires up just channel 1 of each category as a worked example —\nuses one [route] per full address, since chained OSC routing isn't reliable in Max.",
				"patching_rect" : [ 30.0, 20.0, 700.0, 90.0 ],
				"fontsize" : 13.0,
				"numinlets" : 1,
				"numoutlets" : 0
			} },

			{ "box" :  {
				"id" : "obj-udpreceive",
				"maxclass" : "newobj",
				"text" : "udpreceive 9000",
				"patching_rect" : [ 30.0, 130.0, 130.0, 22.0 ],
				"numinlets" : 1,
				"numoutlets" : 1,
				"outlettype" : [ "" ]
			} },

			{ "box" :  {
				"id" : "obj-comment-cv",
				"maxclass" : "comment",
				"text" : "/synapse/cv/1  — float, smoothed DC. Throttled (only sent when changed by ≥ cv_eps).",
				"patching_rect" : [ 30.0, 175.0, 600.0, 20.0 ]
			} },
			{ "box" :  {
				"id" : "obj-rt-cv1",
				"maxclass" : "newobj",
				"text" : "route /synapse/cv/1",
				"patching_rect" : [ 30.0, 200.0, 200.0, 22.0 ],
				"numinlets" : 1,
				"numoutlets" : 2,
				"outlettype" : [ "", "" ]
			} },
			{ "box" :  {
				"id" : "obj-cv1-num",
				"maxclass" : "flonum",
				"text" : "0.",
				"patching_rect" : [ 30.0, 230.0, 80.0, 22.0 ],
				"numinlets" : 1,
				"numoutlets" : 2,
				"outlettype" : [ "", "bang" ]
			} },
			{ "box" :  {
				"id" : "obj-cv1-label",
				"maxclass" : "comment",
				"text" : "ch1 CV value",
				"patching_rect" : [ 120.0, 232.0, 100.0, 20.0 ]
			} },

			{ "box" :  {
				"id" : "obj-comment-gate",
				"maxclass" : "comment",
				"text" : "/synapse/gate/1  — int 0|1, current state every block.",
				"patching_rect" : [ 30.0, 280.0, 480.0, 20.0 ]
			} },
			{ "box" :  {
				"id" : "obj-rt-gate1",
				"maxclass" : "newobj",
				"text" : "route /synapse/gate/1",
				"patching_rect" : [ 30.0, 305.0, 200.0, 22.0 ],
				"numinlets" : 1,
				"numoutlets" : 2,
				"outlettype" : [ "", "" ]
			} },
			{ "box" :  {
				"id" : "obj-gate1-toggle",
				"maxclass" : "toggle",
				"patching_rect" : [ 30.0, 335.0, 28.0, 28.0 ],
				"numinlets" : 1,
				"numoutlets" : 1,
				"outlettype" : [ "int" ],
				"parameter_enable" : 0
			} },
			{ "box" :  {
				"id" : "obj-gate1-label",
				"maxclass" : "comment",
				"text" : "ch1 gate state",
				"patching_rect" : [ 70.0, 339.0, 110.0, 20.0 ]
			} },

			{ "box" :  {
				"id" : "obj-comment-event",
				"maxclass" : "comment",
				"text" : "/synapse/gate_event/1  — string \"rising\"|\"falling\". Bangs only on transitions.",
				"patching_rect" : [ 30.0, 380.0, 540.0, 20.0 ]
			} },
			{ "box" :  {
				"id" : "obj-rt-event1",
				"maxclass" : "newobj",
				"text" : "route /synapse/gate_event/1",
				"patching_rect" : [ 30.0, 405.0, 240.0, 22.0 ],
				"numinlets" : 1,
				"numoutlets" : 2,
				"outlettype" : [ "", "" ]
			} },
			{ "box" :  {
				"id" : "obj-event1-bang",
				"maxclass" : "button",
				"patching_rect" : [ 30.0, 435.0, 28.0, 28.0 ],
				"numinlets" : 1,
				"numoutlets" : 1,
				"outlettype" : [ "bang" ]
			} },
			{ "box" :  {
				"id" : "obj-event1-label",
				"maxclass" : "comment",
				"text" : "ch1 edge bang (rising/falling — use another [route rising falling] to split if needed)",
				"patching_rect" : [ 70.0, 439.0, 600.0, 20.0 ]
			} },

			{ "box" :  {
				"id" : "obj-comment-spectrum",
				"maxclass" : "comment",
				"text" : "/synapse/spectrum/1  — 32 log-spaced magnitude bins, ~30Hz. Audio-role channels only.",
				"patching_rect" : [ 30.0, 480.0, 600.0, 20.0 ]
			} },
			{ "box" :  {
				"id" : "obj-rt-spec1",
				"maxclass" : "newobj",
				"text" : "route /synapse/spectrum/1",
				"patching_rect" : [ 30.0, 505.0, 240.0, 22.0 ],
				"numinlets" : 1,
				"numoutlets" : 2,
				"outlettype" : [ "", "" ]
			} },
			{ "box" :  {
				"id" : "obj-spec1-mslider",
				"maxclass" : "multislider",
				"patching_rect" : [ 30.0, 535.0, 480.0, 90.0 ],
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
				"patching_rect" : [ 520.0, 565.0, 200.0, 20.0 ]
			} },

			{ "box" :  {
				"id" : "obj-comment-extend",
				"maxclass" : "comment",
				"text" : "To extend: copy any [route /synapse/<feat>/1] and change the channel suffix.\nTo forward to Unreal: tap any route's outlet → [udpsend <unreal-host> <unreal-port>].\nFull OSC schema in docs/OSC_SCHEMA.md; full 14-channel receiver in synapse_full.maxpat.",
				"patching_rect" : [ 30.0, 645.0, 800.0, 60.0 ]
			} }
		],
		"lines" : [
			{ "patchline" :  {
				"source" : [ "obj-udpreceive", 0 ],
				"destination" : [ "obj-rt-cv1", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-udpreceive", 0 ],
				"destination" : [ "obj-rt-gate1", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-udpreceive", 0 ],
				"destination" : [ "obj-rt-event1", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-udpreceive", 0 ],
				"destination" : [ "obj-rt-spec1", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-rt-cv1", 0 ],
				"destination" : [ "obj-cv1-num", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-rt-gate1", 0 ],
				"destination" : [ "obj-gate1-toggle", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-rt-event1", 0 ],
				"destination" : [ "obj-event1-bang", 0 ]
			} },
			{ "patchline" :  {
				"source" : [ "obj-rt-spec1", 0 ],
				"destination" : [ "obj-spec1-mslider", 0 ]
			} }
		]
	}
}
