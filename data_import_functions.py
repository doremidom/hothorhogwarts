import base64
import json
import urllib
import os
import re

import requests

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
			if "track" in track_data:
				track = track_data["track"]
				if "preview_url" in track and track["preview_url"] is not None:
					track_source = track["preview_url"]
					track_type = "preview_url"
				else:
					track_source = track["uri"]
					track_type = "spotify_uri"
			track_obj = {
				"label": label,
				"source": track_source,
				"type": track_type
			}
			tracks.append(track_obj)

		print("Retrieved {} tracks with label {} ({} preview URLs, {} Spotify URIs)".format(
			len(["" for track in tracks if track["label"] == label]),
			label,
			len(["" for track in tracks if track["type"] == "preview_url" and track["label"] == label]),
			len(["" for track in tracks if track["type"] == "spotify_uri" and track["label"] == label])
		))

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

