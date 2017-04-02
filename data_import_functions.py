import base64
import json
import os
import random

import requests

def get_embed_contents(source):
	url = "https://embed.spotify.com/?uri={}".format(source)
	resp = requests.get(url)
	return resp.content

# Return data for a single track
def get_single_track_data():
	tracks = [{}]
	if os.environ.get("IS_HEROKU"):
		url = os.environ.get("TRACKS_JSON_URL")
		if url:
			resp = requests.get(url)
			if resp.status_code == 200:
				tracks = json.loads(resp.content)
	else:
		with open("tracks.json", "r") as f:
			tracks = json.loads(f.read())
	return random.choice(tracks)

### The below functions are to be run as needed to update track data and aren't used on the actual web app ###

# Create JSON file with all track data (so we don't have to pull it from Spotify each time)
def create_tracks_json():
	# Get user and playlist IDs
	with open("keys.json", "r") as f:
		data = json.loads(f.read())
	spotify_data = data["spotify"]
	user_id = spotify_data["user_id"]
	hoth_playlist_id = spotify_data["hoth_playlist_id"]
	hogwarts_playlist_id = spotify_data["hogwarts_playlist_id"]
	
	# Get track data
	hoth_playlist = retrieve_playlist_tracks(user_id, hoth_playlist_id)
	hogwarts_playlist = retrieve_playlist_tracks(user_id, hogwarts_playlist_id)
	tracks = []

	# Format track data with labels and relevant info
	for playlist_data in [{"playlist": hoth_playlist, "label": "hoth"}, {"playlist": hogwarts_playlist, "label": "hogwarts"}]:
		playlist = playlist_data["playlist"]
		label = playlist_data["label"]

		for track_data in playlist:
			track_source = ""
			track_type = "spotify_uri" # "spotify_uri" or "preview_url"
			track_image = ""

			if "track" in track_data:
				track = track_data["track"]
				if "preview_url" in track and track["preview_url"] is not None:
					track_source = track["preview_url"]
					track_type = "preview_url"
				else:
					track_source = track["uri"]
					track_type = "spotify_uri"
				if "album" in track:
					album = track["album"]
					if "images" in album and len(album["images"]) > 0:
						images = album["images"]
						# images = [image for image in images if image["width"] > 200]
						# if len(images) > 0:
						#	track_image = images[0]["url"]
						images = sorted(images, key=lambda image: image["width"], reverse=True)
						track_image = images[0]["url"]
			track_obj = {
				"label": label,
				"source": track_source,
				"type": track_type,
				"image": track_image
			}
			tracks.append(track_obj)

		print("Retrieved {} tracks with label {} ({} preview URLs, {} Spotify URIs)".format(
			len(["" for track in tracks if track["label"] == label]),
			label,
			len(["" for track in tracks if track["type"] == "preview_url" and track["label"] == label]),
			len(["" for track in tracks if track["type"] == "spotify_uri" and track["label"] == label])
		))

	print("Images available for {} of {} tracks".format(len(["" for track in tracks if track["image"] != ""]), len(tracks)))

	# Only use tracks with preview URLs
	tracks = [track for track in tracks if track["type"] == "preview_url"]

	# Write to JSON
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

