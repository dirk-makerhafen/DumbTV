#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
sys.dont_write_bytecode = True
import json, os, glob

from kodino import kodinoPlugins

# some known good plugins, add more! 

addons = '''
plugin.video.khanacademy
plugin.video.1channel
plugin.video.3satmediathek
plugin.video.7tvneu
plugin.video.9gag
plugin.video.9gagtv
plugin.video.L0RE.disneychannel
plugin.video.L0RE.spiegeltv
plugin.video.SportsDevil
plugin.video.YouTube_Vault
plugin.video.abcfamily
plugin.video.amaproracing
plugin.video.aob
plugin.video.ardmediathek_de
plugin.video.arte_tv
plugin.video.arteplussept
plugin.video.attactv
plugin.video.br3
plugin.video.break_com
plugin.video.brmediathek
plugin.video.btsportvideo
plugin.video.buzzfeed
plugin.video.chefkoch_de
plugin.video.chipfish
plugin.video.classiccinema
plugin.video.cnn
plugin.video.comedycentral
plugin.video.comettv
plugin.video.comicvine
plugin.video.commingsoon.it
plugin.video.cook
plugin.video.dailymotion
plugin.video.dailymotion_com
plugin.video.daserstemediathek
plugin.video.disneychannel_de
plugin.video.earthcom
plugin.video.empflix
plugin.video.eurosportplayer
plugin.video.f4mTester
plugin.video.fantasticc
plugin.video.featherence.doku
plugin.video.featherence.extreme
plugin.video.featherence.kids
plugin.video.fernsehkritik
plugin.video.fernsehkritik_tv
plugin.video.fitnesszone
plugin.video.fmetalvideo
plugin.video.fox.news
plugin.video.freeview
plugin.video.funkmediathek
plugin.video.gdrive
plugin.video.greenpeace
plugin.video.hrmediathek
plugin.video.hsn
plugin.video.infowars
plugin.video.kahnacademy
plugin.video.kikamediathek
plugin.video.liveleak
plugin.video.lubetube
plugin.video.mediathek
plugin.video.metalvideo
plugin.video.mtv_de
plugin.video.multichannel
plugin.video.myvideo_de
plugin.video.ndrmediathek
plugin.video.nlhardwareinfo
plugin.video.nlhardwareino
plugin.video.nrdmediathek
plugin.video.phoenixmediathek
plugin.video.schaetzederwelt
plugin.video.servustv_com
plugin.video.si
plugin.video.skynews
plugin.video.sportdeutschland_tv
plugin.video.sportschau
plugin.video.srmediathek
plugin.video.tagesschau
plugin.video.tele5_de
plugin.video.tivi_de
plugin.video.tube8
plugin.video.tv3.cat
plugin.video.unithek
plugin.video.vice
plugin.video.videodevil
plugin.video.vimeo
plugin.video.wdrmediathek
plugin.video.wdrrockpalast
plugin.video.weetv
plugin.video.welt_der_wunder
plugin.video.you.jizz
plugin.video.youporn
plugin.video.youtube
plugin.video.ytsf
'''
plugins = kodinoPlugins.KodinoPlugins()
addons = [x.strip() for x in addons.split("\n") if x.strip() != ""]

for addon in addons:
    plugins.install(addon)
