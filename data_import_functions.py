import urllib
import os
import re
import requests

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
