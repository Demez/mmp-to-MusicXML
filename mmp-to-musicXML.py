# current goal: get as many notes as accurately as possible from LMMS to XML for import to MuseScore
# this script is meant to be a quick-and-dirty way to get at least a good portion of the music from an LMMS mmp file to music sheets 
# it's not going to provide a perfect or even mostly complete score, but hopefully should reduce the amount of work required to transcribe 
# music from LMMS's piano roll to say MuseScore. :) 

# future goals: somehow read in a single piano track and be able to figure out which notes should go on the bass staff lol.

# major bugs: 
# - can't handle/identify TRIPLETS! :0 or anything smaller than 64th notes...
# - gotta normalize notes such that they're multiples of 8! i.e. if in LMMS you write down some notes using some smaller division like 1/64,
# what looks like an eighth note (which should have a length of 24) might actually have a length of 25, which will throw everything off!
# - can't do time signatures other than 4/4

# ALSO IMPORTANT: if you're like me I tend to write all my string parts on one track, as well as for piano. unfortunately, this will break things 
# if trying to convert to xml. since there are so many different rhythms and notes you could possibly fit wihtin a single measure, 
# before attempting to convert parts will have to be separated (but doing so in LMMS is not too bad - just a bit of copying, pasting and scrubbing)

from collections import OrderedDict
import xml.etree.ElementTree as ET 
from xml.dom import minidom  # https://stackoverflow.com/questions/28813876/how-do-i-get-pythons-elementtree-to-pretty-print-to-an-xml-file/28814053
import math

### important constants! ###
LMMS_MEASURE_LENGTH = 192
NUM_DIVISIONS = "8" # number of divisions per quarter note (see https://www.musicxml.com/tutorial/the-midi-compatible-part/duration/)
INSTRUMENTS = set(["piano", "bass", "vibes", "orchestra", "violin", "cello", "tuba", "trombone", "french horn", "horn", "trumpet", "flute", "oboe", "clarinet", "bassoon", "street bass", "guitar","str", "marc str","pizz","harp","piccolo"])
BASS_INSTRUMENTS = set(["bass","cello","double bass","trombone","tuba","bassoon","street bass"])
NOTES = {0:'C', 1:'C#',2:'D',3:'D#',4:'E',5:'F',6:'F#',7:'G',8:'G#',9:'A',10:'A#',11:'B'}

# these are the true lengths of each note type.
# for example, a 16th note has a length of 12
# these numbers are based on note lengths in LMMS!
NOTE_TYPE = {"whole":192 , "half":96, "quarter":48, "eighth":24, "16th":12, "32nd":6, "64th":3}

# these are the note types that should be used when given a certain length 
# if no length perfectly matches, then the closest match is the one to use
# these numbers are based on note lengths in LMMS!
# this is too restrictive? 168 should really be a double dotted half note and 144 a dotted half??
NOTE_LENGTHS = {192: "whole", 168: "half", 144: "half", 96: "half", 72: "quarter", 48: "quarter", 36: "eighth", 24: "eighth", 12: "16th", 6: "32nd", 3: "64th"}

CLEF_TYPE = {"treble": {"sign": "G", 'line': "2"}, "bass": {"sign": "F", "line": "4"}}

### helpful functions ###
	
# for a given length, find the closest note type 
# this function attemps to find the closest, largest length that's less than or equal to the given length 
# returns the closest note type match (i.e. half, quarter, etc.)
def findClosestNoteType(length):
	
	closestLength = None
	
	for noteLength in sorted(NOTE_LENGTHS, reverse=True):
		if noteLength <= length:
			return NOTE_LENGTHS[noteLength]
				
	if closestLength == None:
		return NOTE_LENGTHS[3]

# add a new note 
# can specify if adding a new note to a chord (which appends a chord element)
# can also supply a lengthTable, which maps the note positions to the smallest-length-note at each position
def addNote(parentNode, note, isChord=False, lengthTable=None):

	pitch = NOTES[int(note.attrib["key"]) % 12]
	position = int(note.attrib["pos"])
	newNote = ET.SubElement(parentNode, "note")
	
	# if note belongs to chord 
	if isChord:
		newChord = ET.SubElement(newNote, "chord")
	
	newPitch = ET.SubElement(newNote, "pitch")
	newStep = ET.SubElement(newPitch, "step")
	newStep.text = str(pitch[0])
	
	if len(pitch) > 1 and pitch[1] == '#':
		newAlter = ET.SubElement(newPitch, "alter")
		newAlter.text = "1"
	
	# calculate octave 
	octave = int(int(note.attrib["key"]) / 12) # basically floor(piano key number / 12)
	newOctave = ET.SubElement(newPitch, "octave")
	newOctave.text = str(octave)
	
	# do some math to get the duration given length of note 
	noteLength = int(note.attrib["len"])

	if lengthTable != None:
		# when would it be None?
		# note that the note length is actually the corrected length
		# this is because I'm not handling dotted notes right now so that if you use the actual length given by LMMS,
		# you're going to skip out on some rests and throw everything off 
		# instead take the note's original length but use NOTE_LENGTHS and NOTE_TYPE to get the corrected length
		noteLength = NOTE_TYPE[findClosestNoteType(lengthTable[position])] #lengthTable[position]
	
	newDuration = ET.SubElement(newNote, "duration")
	newDuration.text = str(int(noteLength/6))
	
	# need to identify the note type 
	newType = ET.SubElement(newNote, "type")
	newType.text = findClosestNoteType(noteLength)
	
	return newNote
	
# add a new rest of a specific type
# see here for possible types: https://usermanuals.musicxml.com/MusicXML/Content/ST-MusicXML-note-type-value.htm
def addRest(parentNode, type):
	# you will need to figure out the duration given the type! i.e. 16th = duration of 2 if divisions is 8 
	# so if divisions = 8, then the smallest unit is 32nd notes, since 8 32nd notes go into 1 quarter note 
	newNote = ET.SubElement(parentNode, "note")
	newRest = ET.SubElement(newNote, "rest")
	newDuration = ET.SubElement(newNote, "duration")
	
	# calculate the correct duration text depending on type 
	# note that this also depends on divisions!
	# assuming division = 8 here!
	# since a duration of 1 = 1 32nd note, we can use 
	dur = ""
	if type == "32nd":
		dur = "1"
	elif type == "16th":
		dur = "2" # 2 32nd notes = 1 16th note 
	elif type == "eighth":
		dur = "4"
	elif type == "quarter":
		dur = "8"
	elif type == "half":
		dur = "16"
		
	newDuration.text = dur
	
	newType = ET.SubElement(newNote, "type")
	newType.text = type
	return newNote 

	
# figure out types and number of rests needed given a length from one note to another 
def getRests(initialDistance):

	restsToAdd = OrderedDict()
	
	# how many whole rests? 
	numWholeRests = int(initialDistance/LMMS_MEASURE_LENGTH)
	remSize = initialDistance - numWholeRests*LMMS_MEASURE_LENGTH
	
	# how many quarter rests? 
	numQuarterRests = int(remSize/48)
	remSize = remSize - numQuarterRests*48 
	
	# how many eighth rests?
	numEighthRests = int(remSize/24)
	remSize = remSize - numEighthRests*24 
	
	# how many 16th rests?
	num16thRests = int(remSize/12)
	remSize = remSize - num16thRests*12 
	
	# how many 32nd rests?
	num32ndRests = int(remSize/6)
	remSize = remSize - num32ndRests*6 
	
	# how many 64th rests? only go up to 64 for now?
	num64thRests = int(remSize/3)
	remSize = remSize - num64thRests*3 
	
	restsToAdd['64th'] = num64thRests
	restsToAdd['32nd'] = num32ndRests
	restsToAdd['16th'] = num16thRests
	restsToAdd['eighth'] = numEighthRests
	restsToAdd['quarter'] = numQuarterRests
	restsToAdd['whole'] = numWholeRests

	return restsToAdd 


# create a measure node 
def createMeasure(parentNode, measureCounter):
	newMeasure = ET.SubElement(parentNode, "measure")
	newMeasure.set("number", str(measureCounter))
	return newMeasure 
	
# create initial measure 
# every first measure of an instrument needs some special properties like clef 
# all first measures have an attribute section, but if it's a rest measure there are additional fields 
def createFirstMeasure(parentNode, measureCounter, clefType, isRest=False):
	
	firstMeasure = createMeasure(currentPart, measureCounter)
	
	newMeasureAttributes = ET.SubElement(firstMeasure, "attributes")
	
	# for the first measure, we need to indicate divisions, clef, key
	# for divisions, this is how much a quarter note will be subdivided
	# so if you have only eighth notes as the smallest unit in your piece, 
	# use 2 if 16th is the smallest, use 4, etc. 
	# how to know this programatically though? iterate through all notes just to 
	# see first??? just go with 8 for now (so 32nd notes are the smallest unit)
	divisions = ET.SubElement(newMeasureAttributes, "divisions")
	divisions.text = NUM_DIVISIONS
	
	key = ET.SubElement(newMeasureAttributes, "key")
	fifths = ET.SubElement(key, "fifths")
	fifths.text = "0"
	
	time = ET.SubElement(newMeasureAttributes, "time")
	timeBeats = ET.SubElement(time, "beats")
	timeBeats.text = "4" # get this information from the top of the mmp file!
	timeBeatType = ET.SubElement(time, "beat-type")
	timeBeatType.text = "4" # get this information from the top of the mmp file!

	# this needs to be changed depending on instrument!!
	newClef = ET.SubElement(newMeasureAttributes, "clef")
	clefSign = ET.SubElement(newClef, "sign")
	clefSign.text = CLEF_TYPE[clefType]["sign"] #"G" 
	clefLine = ET.SubElement(newClef, "line")
	clefLine.text = CLEF_TYPE[clefType]["line"] #"2"
	
	if isRest:
		newNote = ET.SubElement(firstMeasure, "note")
		newRest = ET.SubElement(newNote, "rest")
		newRest.set("measure", "yes")
		newDuration = ET.SubElement(newNote, "duration")
		newDuration.text = "32"
		
	return firstMeasure 
	
# add a complete measure of rest 
def addRestMeasure(parentNode, measureCounter):
	newRestMeasure = ET.SubElement(parentNode, "measure")
	#newRestMeasure.set("implicit", "yes")
	newRestMeasure.set("number", str(measureCounter))
	
	# make sure to add rest element in 'note' section 
	newNote = ET.SubElement(newRestMeasure, "note")
	newRest = ET.SubElement(newNote, "rest")
	newRest.set("measure", "yes")
	newDuration = ET.SubElement(newNote, "duration")
	newDuration.text = "32" # should be beats * duration - here is 32 because 4 beats, each beat has 8 subdivisions 

	return newRestMeasure # return a reference to the newly created measure node 

# checks if a new measure should be added given the current length of notes
# the length passed should be calculated by createLengthTable() so that currLength will always eventually be a value where mod 192 is 0
def newMeasureCheck(currLength):
	return currLength%LMMS_MEASURE_LENGTH == 0
	
# creates a new measure and returns a reference to it 
def addNewMeasure(parentNode, measureNum):
	currMeasure = ET.SubElement(parentNode, "measure")
	currMeasure.set("number", str(measureNum))
	return currMeasure 

# takes list of notes 
# returns what the length of each note at each position should be 
def createLengthTable(notes):
	lengthTable = {} 
	
	# also truncate some lengths as needed if they carry over to the next measure?
	# example: look at the 2nd-to-last and last notes. 372 + 48 > 384, but 384 is the next measure.
	# so therefore if we didn't have any other notes at that position except the one with length 48, 
	# the 2nd-to-last note's length should be truncated to 12, the smallest length at that position
	# that does not carry over to the next measure.
	#
	#  <note pan="0" key="79" vol="48" pos="372" len="48"/>
	#  <note pan="0" key="67" vol="48" pos="372" len="48"/> <=
	#  <note pan="0" key="77" vol="48" pos="384" len="48"/> <=
	#
	# we also have to truncate notes within the same measure
	# example: the 2nd note below happens before the 1st note ends.
	#
	#  <note pan="0" key="67" vol="97" pos="192" len="96"/>
    #  <note pan="0" key="60" vol="82" pos="216" len="48"/>
    #  <note pan="0" key="62" vol="87" pos="264" len="96"/>
	#
	# this scenario also:
	# the note at post 144 becomes a half note and makes the current measure too large by a quarter note 
	# pos: 144, len: 240, measure: 1
	# pos: 240, len: 144, measure: 2
	# this scenario is remedied by only updating the length table if a new smaller length is found for a position already in the table 
	
	nextMeasurePos = LMMS_MEASURE_LENGTH
	for i in range(0, len(notes)):
		note = notes[i][0]
		p = int(note.attrib["pos"])
		l = int(note.attrib["len"])
		
		if p in lengthTable:
		
			if l < lengthTable[p]:
				lengthTable[p] = l 
			
			# there might be an instance where we have at least 2 notes in the same position,
			# but they're the same length AND they should actually be truncated because they
			# spill over into another note like in the second if statement below (in the else block) 
			# so we need to check that here 
			if i < len(notes)-1 and ((l + p) > int(notes[i+1][0].attrib["pos"])) and p != int(notes[i+1][0].attrib["pos"]):
				nextNotePos = int(notes[i+1][0].attrib["pos"])
				
				# but the new length must be smaller in order to be updated 
				if nextNotePos - p < lengthTable[p]:
					lengthTable[p] = nextNotePos - p 
			
		else:
			currMeasurePos = (notes[i][1]-1)*LMMS_MEASURE_LENGTH # notes[i][1]-1 is the measure number 
			nextMeasurePos = currMeasurePos + LMMS_MEASURE_LENGTH
			
			# we want to know if this current note carries over into the next measure 
			# to find out we can see if the current note's position plus its length is greater than the next measure's position (i.e. this note spills over into the next measure)
			currNoteDistance = p + l 

			if currNoteDistance > nextMeasurePos:
				# truncate the note so that its length it goes only up to the next measure's position 
				l = nextMeasurePos - p  
			
			if i < len(notes)-1:
				prevNotePos = int(notes[i+1][0].attrib["pos"])
				if ((l + p) > prevNotePos) and p != prevNotePos:
					# similar to above, but checking if current note's length overlaps with the next note's position. 
					# if the current note ends after the next note starts, truncate the current note's length
					# the new length will be the difference between the next note's position and the current note's position
					# it's also important to check that this current note is not in the same position as the next note (which forms a chord)
					# we need this check because otherwise we might get a 0 for l's value 
					nextNotePos = int(notes[i+1][0].attrib["pos"])
					l = nextNotePos - p 
					#print(str(l) + ", l+p: " + str(l+p) )

			lengthTable[p] = l
			#print(lengthTable)
			
	return lengthTable 


### START PROGRAM ###
# https://stackabuse.com/reading-and-writing-xml-files-in-python/
tree = ET.parse('testfiles/hatarakusaibouED-arr.mmp') #'testfiles/080415pianobgm3popver.mmp' #'testfiles/011319bgmidea.mmp' #'testfiles/funbgmXMLTEST.mmp' #'testfiles/funbgmXMLTESTsmall.mmp' #'testfiles/yakusoku_no_neverlandOP_excerpt_pianoarr.mmp'
root = tree.getroot()

# get the time signature of the piece 
timeSignatureNumerator = root.find('head').attrib['timesig_numerator']
timeSignatureDenominator = root.find('head').attrib['timesig_denominator']
#print('the time signature is: ' + str(timeSignatureNumerator) + "/" + str(timeSignatureDenominator))

if timeSignatureNumerator != '4' or timeSignatureDenominator != '4':
	print('time signature is not 4/4. your file might not come out too well :( sorry!')
	
# if we come across an empty instrument (i.e. no notes), put their PART ID (i.e. 'P1') in this list. then at the end we look for nodes containing these names and delete them.
emptyInstruments = []

# write a new xml file 
newFile = open("newxmltest.xml", "w")

# add the appropriate headers first 
newFile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
newFile.write('<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">\n')

# create the general tree structure, then fill in accordingly
scorePartwise = ET.Element('score-partwise')

# title of piece
movementTitle = ET.SubElement(scorePartwise, 'movement-title')
movementTitle.text = "title of piece goes here"

# list of the instrument parts 
partList = ET.SubElement(scorePartwise, 'part-list')

# then go through each instrument in the mmp file and add them to part-list 
instrumentCounter = 1
for el in tree.iter(tag = 'track'):
	name = el.attrib['name']
	if name in INSTRUMENTS:
		newPart = ET.SubElement(partList, "score-part")
		newPart.set('id', "P" + str(instrumentCounter))
		instrumentCounter += 1
		
		newPartName = ET.SubElement(newPart, "part-name")
		newPartName.text = name


# now that the instruments have been declared, time to write out the notes for each instrument 
# for each instrument, we need to write out each measure by noting the properties of each measure
# then we write out each note in each measure 

# potential problems:
# the xml file for a LMMS project might not actually have the notes in order for an instrument!!! 
# notes in LMMS are separated in chunks called 'patterns' in the XML file (.mmp). each pattern has 
# a position, so use that to sort the patterns in order. then write out the notes 
instrumentCounter = 1 	# reset instrumentCounter 

# we need to keep track of each part - ther part id node and the last measure num they had notes for. 
# at the very end we need to make sure every part has the same number of measures 
partMeasures = {}

# for each track element
for el in tree.iter(tag = 'track'):

	name = el.attrib['name']
	
	if name in INSTRUMENTS:
		
		# for each valid instrument el, create a new part section that will hold its measures and their notes
		currentPart = ET.SubElement(scorePartwise, "part");
		currentPart.set("id", "P" + str(instrumentCounter))
		
		# get the pattern chunks (which hold the notes)
		patternChunks = []
		for el2 in el.iter(tag = 'pattern'):
			patternChunks.append(el2)
		
		currMeasure = None
		patternNotes = []
		
		# concatenate all the patterns and get their notes all in one list 
		for i in range(0, len(patternChunks)):
			# get the position of the pattern. note that a pattern might not start at position 0!
			# if it doesn't start at 0 and it's the first pattern, or the current chunk doesn't start
			# where the previous chunk left off, then you need to make rest measures to fill in any gaps. 
			# another LMMS xml file property -> every measure is of length 192, so each measure's position 
			# is a multiple of 192 
			chunk = patternChunks[i].iter(tag = 'note')
			chunkPos = int(patternChunks[i].attrib["pos"])
			measureNum = int(chunkPos / LMMS_MEASURE_LENGTH) + 1 # patterns always start on a multiple of 192 
			
			for n in chunk:
				# because each note's position is relative to their pattern, each note's position should be their pattern pos + note pos 
				# but an important piece of information is what measure this note falls in. we can find out what measure this note is in 
				# by first getting the chunk's position and dividing it by 192 -> this gets us the starting measure number of the chunk 
				# we can also know what measure the chunk ends at given its length (I don't think we need this info though for this)
				# so then for each note in the chunk, we keep a counter that accumulates note lengths seen so far 
				# as soon as that counter equals or exceeds 192, we reset it to 0 and increment the measure count 
				# we'll record the measure in a tuple along with a reference to the note, i.e. (noteReference, measureNumber)
				notePos = int(n.attrib["pos"])			
				newPos = chunkPos + notePos 
				n.set("pos", str(newPos))
				
				# increment measure num if needed
				if newPos >= (measureNum*LMMS_MEASURE_LENGTH):
					# if note is within the next measure over 
					if newPos < ((measureNum+1)*LMMS_MEASURE_LENGTH):
						measureNum += 1
					else:
						# the newPos might actually be 2 measures over, not just the next measure! 
						# need to add 1 because positions start at 0
						measureNum = int(math.ceil(newPos / LMMS_MEASURE_LENGTH)) + 1
				
				patternNotes.append((n, measureNum))
					
		# sort the notes in the list by position
		# remember that the elements are tuples => (note, the measure note is in)
		patternNotes = sorted(patternNotes, key=lambda p : int(p[0].attrib["pos"]))

		# this is very helpful for checking notes 
		#if name == 'horn':
		#print("----- " + str(name) + " ------------------")
		#for p in patternNotes:
		#	print("pos: " + str(p[0].attrib["pos"]) + ", len: " + str(p[0].attrib["len"]) + ", measure: " + str(p[1]))
		#print("-----------------------")
			
		notes = patternNotes 
		
		# this instrument might not have any notes! (empty track)
		# if so, need to remove this subelement node at the very  end otherwise MuseScore will complain... (the xml is valid, i.e. it's an empty tag but MuseScore doesn't like that)
		if len(notes) == 0:
			emptyInstruments.append("P" + str(instrumentCounter))
			continue
			
		# find out what the smallest note length should be for stacked notes in a chord
		# this unfortunately means tied notes will be broken
		positionLengths = createLengthTable(notes)
		#print(positionLengths)
		
		# first create the first measure for this intrument. it might be a rest measure, 
		# or rest measures might need to be added first!
		firstNotePos = int(notes[0][0].attrib["pos"])
		firstNoteMeasureNum = notes[0][1]

		if firstNoteMeasureNum == 1:
			# if first note starts from the very beginning, create initial measure without any rests padding
			if name in BASS_INSTRUMENTS:
				currMeasure = createFirstMeasure(currentPart, firstNoteMeasureNum, "bass", False)
			else:
				currMeasure = createFirstMeasure(currentPart, firstNoteMeasureNum, "treble", False)
		else:			
			# add whole rests first 
			numWholeRests = firstNoteMeasureNum -1
			
			for i in range(0, numWholeRests):
				if i == 0:
					#createFirstMeasure(currentPart, i + 1, True)
					if name in BASS_INSTRUMENTS:
						createFirstMeasure(currentPart, i + 1, "bass", True)
					else:
						createFirstMeasure(currentPart, i + 1, "treble", True)
				else:
					addRestMeasure(currentPart, i + 1)
			
			currMeasure = addNewMeasure(currentPart, firstNoteMeasureNum)
			
		lastMeasureNum = firstNoteMeasureNum 
		
		# then go through the notes
		partMeasures[currentPart] = 0 	# keep track of how many measures this instrument has 
		positionsSeen = set()
		for k in range(0, len(notes)):
		
			note = notes[k][0]
			noteLen = int(notes[k][0].attrib["len"])
			measureNum = notes[k][1]
			
			position = int(note.attrib["pos"])
			pitch = NOTES[int(note.attrib["key"]) % 12]
			
			# since the notes list contains tuples where tuple[0] is the note object, and tuple[1] is the measure the note should go in, we can use this info 
			if lastMeasureNum == measureNum:
				
				# add the note (but check to see if it belongs to a chord!)
				if position in positionsSeen:	
					# this note is part of a chord 
					addNote(currMeasure, note, True, positionLengths)
				else:
					# add rests if needed based on previous note's position, then add the note 
					if k > 0:
						prevNotePos = int(notes[k-1][0].attrib["pos"])
						restsToAdd = getRests(position -  (prevNotePos  + NOTE_TYPE[findClosestNoteType(positionLengths[prevNotePos])]))
					else:
						restsToAdd = getRests(position - ((measureNum-1)*LMMS_MEASURE_LENGTH))
				
					for rest in restsToAdd:
						for l in range(0, restsToAdd[rest]):
							addRest(currMeasure, rest)
						
					positionsSeen.add(position)
					addNote(currMeasure, note, False, positionLengths)
				
				# pad the rest of the measure with rests if needed (i.e. this is the last note of this measure)
				if (k < len(notes) - 1 and notes[k+1][1] > measureNum ) or (k == (len(notes) - 1)):
					size = (measureNum*LMMS_MEASURE_LENGTH) - (position + NOTE_TYPE[findClosestNoteType(positionLengths[position])])
					padRestsToAdd = getRests(size)
					for rest in padRestsToAdd:
						for l in range(0, padRestsToAdd[rest]):
							addRest(currMeasure, rest)
			else:
				# need to create new measure(s), then add the note
				if k > 0:
					numWholeRests = measureNum - lastMeasureNum - 1
					for i in range(0, numWholeRests):
						addRestMeasure(currentPart, notes[k-1][1] + i + 1)
						
					# create the new measure to place the note 
					currMeasure = addNewMeasure(currentPart, measureNum)
					
					# add the note (but check to see if it belongs to a chord!)
					if position in positionsSeen:	
						# make new note but add to a chord
						# no need to check if need to make a new measure because these notes are in a chord 
						addNote(currMeasure, note, True, positionLengths)
					else:
						# this might be reached when adding the first note of a new measure 
						restsToAdd = getRests(position - ((measureNum-1)*LMMS_MEASURE_LENGTH))
					
						for rest in restsToAdd:
							# add rests smaller than whole rests 
							for l in range(0, restsToAdd[rest]):
								addRest(currMeasure, rest)
								
						# then add the note 
						positionsSeen.add(position)
						addNote(currMeasure, note, False, positionLengths)
						#print(str(restsToAdd))
						#print(positionLengths)
					
					# pad the rest of the measure with rests if needed (i.e. this is the last note of this measure)
					# scenarios that could trigger this condition: 1 measure with a single note 
					if (k < len(notes) - 1 and notes[k+1][1] > measureNum ) or (k == (len(notes) - 1)):
						padRestsToAdd = getRests((measureNum*LMMS_MEASURE_LENGTH) - (position+NOTE_TYPE[findClosestNoteType(positionLengths[position])]))
						for rest in padRestsToAdd:
							for l in range(0, padRestsToAdd[rest]):
								addRest(currMeasure, rest)
			
			partMeasures[currentPart] = measureNum
			lastMeasureNum = measureNum
		
		# move to next instrument
		instrumentCounter += 1
		
# still need to add whole rests to the end of each instrument so they all have the same number of measures total, otherwise a corrupt file will be reported (but it will still work, at least in MuseScore)!
highestNumMeasures  = 0
for part in partMeasures:
	if partMeasures[part] > highestNumMeasures:
		highestNumMeasures = partMeasures[part]
		
for part in partMeasures:
	if partMeasures[part] < highestNumMeasures:
		for i in range(partMeasures[part]+1, highestNumMeasures+1):
			addRestMeasure(part, i)
		
# check if we need to remove any nodes for empty instruments 
for partID in emptyInstruments:
	for part in scorePartwise.findall("part"):
		if part.attrib['id'] == partID:
			scorePartwise.remove(part)
			
	# remove from part list 
	for part in partList.findall('score-part'):
		if part.attrib['id'] == partID:
			partList.remove(part)
			

# write tree to file 
# make sure to pretty-print because otherwise everything will be on one line
data = minidom.parseString(ET.tostring(scorePartwise, encoding="unicode")).toprettyxml(indent="    ")
data = data.replace("<?xml version=\"1.0\" ?>", "") # toprettyxml adds a xml declaration, but I have it already written to the file
newFile.write(data)

#for el in tree.iter(tag = 'track'):
#	print(el.attrib['name'])