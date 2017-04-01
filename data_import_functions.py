import base64
import json
import urllib
import os
import re

import requests

# Create JSON file with all track data (so we don't have to pull it from Spotify each time)
def create_tracks_json():
	with open("keys.json", "r") as f:
		data = json.loads(f.read())
	spotify_data = data["spotify"]
	user_id = spotify_data["user_id"]
	hoth_playlist_id = spotify_data["hoth_playlist_id"]
	hogwarts_playlist_id = spotify_data["hogwarts_playlist_id"]
	
	hoth_playlist = retrieve_playlist_tracks(user_id, hoth_playlist_id)
	hogwarts_playlist = retrieve_playlist_tracks(user_id, hogwarts_playlist_id)
	tracks = []

	for playlist_data in [{"playlist": hoth_playlist, "label": "hoth"}, {"playlist": hogwarts_playlist, "label": "hogwarts"}]:
		playlist = playlist_data["playlist"]
		label = playlist_data["label"]
		
		playlist = [
			{
				"preview_url": track_data["track"]["preview_url"],
				"label": label
			}
		for track_data in playlist
		if "track" in track_data and "preview_url" in track_data["track"] and track_data["track"]["preview_url"] is not None
		]

		print("Preview URLs available for {} tracks with label {}".format(len(playlist), label))

		tracks.extend(playlist)

	with open("tracks.json", "w") as f:
		f.write(json.dumps(tracks))

# Retrieve all tracks in a given playlist
def retrieve_playlist_tracks(user_id, playlist_id):
	endpoint = "https://api.spotify.com/v1/users/{}/playlists/{}/tracks".format(user_id, playlist_id)
	token = get_access_token()
	headers = {"Authorization": "Bearer %s" % token}
	tracks = []
	has_next = True

	while has_next:
		resp = requests.get(endpoint, headers=headers)
		if resp.status_code == 200:
			data = json.loads(resp.content)
			tracks.extend(data["items"])
			endpoint = data["next"]
			if not endpoint:
				has_next = False
		else:
			has_next = False

	print("Retrieved {} tracks".format(len(tracks)))
	return tracks


# Get an access token: based on Client Credentials Flow at
# https://developer.spotify.com/web-api/authorization-guide/#client-credentials-flow
def get_access_token():
	credentials = get_client_credentials()
	encoded_credentials = base64.b64encode("{}:{}".format(credentials["client_id"], credentials["client_secret"]))
	endpoint = "https://accounts.spotify.com/api/token"
	headers = {"Authorization": "Basic {}".format(encoded_credentials)}
	params = {"grant_type": "client_credentials"}
	resp = requests.post(endpoint, data=params, headers=headers)
	if resp.status_code == 200:
		data = json.loads(resp.content)
		token = data["access_token"]
		return token
	else:
		return "ERROR {}".format(resp.status_code)

def get_client_credentials():
	client_id = ""
	client_secret = ""
	if os.environ.get("IS_HEROKU"):
		# TODO
		pass
	else:
		with open("keys.json", "r") as f:
			data = json.loads(f.read())
			spotify_data = data["spotify"]
			client_id = spotify_data["client_id"]
			client_secret = spotify_data["client_secret"]
	return {
		"client_id": client_id,
		"client_secret": client_secret
	}


################################################################

#directory for local images
directory = "tmp"

#creates a post
def importer(artist, image =''):
	artist_info = retrieve_artist_info(artist, image)

	#create wordpress post
	wp_id = wp.create_post(artist_info)

	artist_info['post_link'] = wp_link(wp_id)

	return artist_info
	

def retrieve_artist_info(artist,image=''):
	artist_output = {'name':artist, 'image':image, 'mbid':get_mbid(artist)}

	# #retrieve list of genres from spotify, (currently unnecessary, using wiipedia)
	# genres = get_genres(artist)

	wiki_info = get_wiki_info(artist)

	# #retrieve social links
	socials = get_social_links(artist)

	# for key, value in socials.items():
	# 	print type(value)

	artist_output['socials'] = socials

	artist_output['summary'] = get_summary(artist)

	artist_output['wiki'] = wiki_info

	
	return artist_output

def download_image(img_url, img_name):

	img_path = "tmp/thumbnails/"+img_name


	urllib.urlretrieve(img_url, img_path)

def crop_image(image_name):
	image = Image.open(os.path.join(directory,image_name))

	w, h = image.size
	image = image.crop((0, 45, w, (h-45)))

	image.save(os.path.join(directory, image_name))

def resize_image(image):
	width = 1120
	height = 630

	directory = "tmp/thumbnails/"

	# Open the file.
	img = Image.open(os.path.join(directory, image))
	 
	# Resize it.
	img = img.resize((width, height), Image.BILINEAR)
	 
	# Save it back to disk.
	img.save(os.path.join(directory, image))

#make image title from post title
def create_img_title(post_title):
	filename = re.sub(r'^\W+', '', re.sub(r'\W+$', '', re.sub(r'\W+', '-', post_title.lower())))
	filename += '.jpg'
	return filename

def add_image(img_url,img_name):
	img_path = directory+img_name
	#download image locally
	download_image(img_url, img_name)
	

	#double check youtube images
	if 'youtube' in img_url:
		img = Image.open(os.path.join(directory, img_name))
		width,height = img.size
		if width < 1280:
			img_url = img_url.replace('maxresdefault','hqdefault')

			download_image(img_url, img_name)

			resize_image(img_name)

	#upload it to wordpress
	img_id = wp.upload_image(img_path)

	return img_id

def wp_link(post_id):
	#determine host from environment variables
	if os.environ.get("IS_PRODUCTION"):
		# print 'heroku env!'
		host = "zumic.com"
	else:
		host = "dev2.zumic.com"

	link = host+"?post_type=artists&p="+post_id+"&preview=true"

	return link


def upload_image_return_id(media_info, source, post_object, artist_name=''):
	#uploading image thumbnail from video id
	img_url = featured_img_url(media_info, source)

	if img_url:
		img_name = create_img_title(post_object['title'])

		img_id = add_image(img_url, img_name)
	else:
		img_id == None

	return img_id


def get_genres(artist):
	artist = artist.replace(' ', '%20')
	spotify_url = "https://api.spotify.com/v1/search?q=artist:"+artist+"&type=artist"

	genres = None

	response = requests.get(spotify_url)

	json = response.json()

	artist_list = json['artists']['items']

	for a in artist_list:
		if a['name'].lower() == artist.lower():
			genres = a['genres']
			return genres 

	return genres

def get_wiki_info(artist):
	info_box = None

	wiki_page = get_wiki_page(artist)

	if wiki_page:

		html_page = wiki_page_to_html(wiki_page)

		#retrieve the info box from the wiki page
		info_box = get_wiki_info_box(html_page)

	return info_box

def get_wiki_info_box(page):
	info_box = page.find("table", class_="infobox")
	# print info_box
	info = parse_info_box(info_box)
	return info

def parse_info_box(info):
	output = {}
	section_keys = info.find_all("th")
	section_values = info.find_all("td")
	section_keys_cleaned = []
	section_values_cleaned = []

	# print len(section_keys)
	# print len(section_values)

	for x in section_keys:
		#remove section header
		if 'colspan' not in x.attrs:
			section_keys_cleaned.append(unicodedata.normalize("NFKC", x.string))
		else:
			print 'skipping:'
			print x
			print ' '

	for y in section_values:
		#remove headers and image descriptions
		if y.find('b') or 'colspan' in y.attrs:
			continue
		elif y.string and y.string != '':
			section_values_cleaned.append(unicode(y.string))
		else:
			data = []
			links = y.find_all('a')
			spans = y.find_all('span')
			
			if links:
				for link in links:
					data.append(link)
			if spans:
				for span in spans:
					data.append(span)


			section_values_cleaned.append(data)

	wiki_info_dict = dict(zip(section_keys_cleaned, section_values_cleaned))

	output = extract_wiki_dict(wiki_info_dict)

	return output


def extract_wiki_dict(wiki_dict):
	info = {}
	print 'INFO:'
	print wiki_dict

	data_names = ['Origin', 'Genres', 'Years active', 'Labels', 'Associated acts', 'Website', 'Members']
	for data in data_names:
		#add check for unicode titles
		if data in wiki_dict:
			if data == 'Website':
				site = wiki_dict['Website']
				#only take in one official site
				if len(site) > 1:
					site = site[0]
								
				site_link = site.attrs['href']

				info['Website'] = site_link
			else:
				#if multiple links, get each
				if type(wiki_dict[data]) is list:
					values = []
					for d in wiki_dict[data]:
						if data == 'Genres':
							if '[' not in d.string:
								values.append(unicode(d.string.title()))
						else:
							values.append(unicode(d.string))
					info[data] = values
				else:
				#else just push the string
					info[data] = unicode(wiki_dict[data])
		else:
			print data + ' not found'


	# for key, value in info.items():
	# 	print key
	# 	print type(value)

	return info
	
def get_mbid(artist):
	m.set_useragent('Zumic Artistfiller', '1.0', 'http://zumic.com')

	artist_info = m.search_artists(artist=artist, strict=True)

	# print artist_info

	info = {'id':None}

	for a in artist_info['artist-list']:
		if a['name'] == artist:
			info = a  

			break

	mbid = info['id']

	# print mbid
	return mbid  

def get_social_links(artist):
	socials = None
	#get id from music brainz
	mbid = get_mbid(artist)

	if mbid:
		mb_profile = 'https://musicbrainz.org/artist/' + mbid

		#get the page
		page = requests.get(mb_profile, verify=False)

		#get beautiful soup of page
		profile_html = BeautifulSoup(page.content, 'html.parser')

		#get the links
		links = bs_profile_to_social(profile_html)

		#parse them
		socials = social_links_to_dict(links)


	return socials



#returns a hash of all social links
def bs_profile_to_social(page):
	socials = {}
	link_table = page.find('ul', class_='external_links')

	links = link_table.find_all('a')

	links_cleaned = []

	#strip all info except href
	for l in links:
		links_cleaned.append(l['href'])

	
	return links_cleaned

def social_links_to_dict(links):
	socials = {}
	#sites to look for
	sites = ['youtube', 'myspace', 'spotify', 'bandcamp','discogs','allmusic', 'last.fm', 'genius', 'imvdb','rateyourmusic','residentadvisor', 'instagram', 'itunes', 'twitter','facebook','soundcloud','wikipedia']

	for link in links:
		for site in sites:
			if site in link:
				site_link = link
				#remove leading //
				if site_link[0:2] == '//':
					site_link = site_link[2:-1]

				socials[site] = site_link
	return socials 

def get_wiki_page(artist):
	wiki_page = None
	#retrieve page from wikipedia
	try:
		wiki_page = wikipedia.page(artist)
	except Exception, e:
		print 'disam found, adding musician'
		wiki_page = wikipedia.page(artist + ' (musician)')

	return wiki_page


def wiki_page_to_html(wiki_page):
	#make wiki object html object for beautiful soup
	artist_page = BeautifulSoup((wiki_page.html()), 'html.parser')

	return artist_page

def get_summary(artist):
	#get a summary about the artist
	try:
		summary = wikipedia.summary(artist, sentences=1)
	except Exception, e:
		summary = wikipedia.summary((artist + ' (musician)'), sentences=1)

	return summary 
