
import pandas as pd 

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import os
from pathlib import Path
import sys
from sklearn.preprocessing import StandardScaler

import warnings
warnings.filterwarnings('ignore')


class Spotify:

    def __init__(self, searched_artist, my_id, my_secret):

        # Get your API account ID and Secret
        self.my_id = my_id
        self.my_secret = my_secret

        # Initialize spotify API with spotipy
        self.spotify = self._initialize_spotipy()

        self.searched_artist = searched_artist

        self.result_artists_df, self.top_song_df, self.all_albums_df, self.all_song_general_info_df, self.all_song_feature_df = self._get_artist_data_wrapper()


    def _initialize_spotipy(self):
        
        # Set credential
        ccm = SpotifyClientCredentials(client_id = self.my_id, 
                                       client_secret = self.my_secret)

        spotify = spotipy.Spotify(client_credentials_manager = ccm)


        return spotify
        
    def _get_artist_data_wrapper(self):


        result_artists_df, self.artist_url = self._get_artist_info()
        top_song_df = self._get_top_songs()
        all_albums_df = self._get_all_albums()
        all_song_general_info_df, all_song_feature_df = self._get_all_songs(all_albums_df)

        return result_artists_df, top_song_df, all_albums_df, all_song_general_info_df, all_song_feature_df


    def _get_artist_info(self):
        '''
        Get Artist general information based on init param. 

        return result_artists_df: pd.DataFrame
        '''


        results = self.spotify.search(self.searched_artist, limit=5, offset=0, type='artist', market=None)

        result_list = []
        for idx, artist in enumerate(results['artists']['items']):
            result_list.append({'artist': artist['name'], 
                                            'followers': artist['followers']['total'], 
                                            'popularity': artist['popularity'], 
                                            'genres': artist['genres'], 
                                            'external_urls': artist['external_urls']['spotify'], 
                                            'artist': artist['name'],       
                                            'href': artist['href'], 
                                            'id': artist['id'], 
                                            'uri': artist['uri']
            })
            
        result_artists_df = pd.DataFrame(result_list).sort_values(by = ['followers'], ascending = False)

        # Get search result 
        result_artists_df = result_artists_df[result_artists_df['artist']==self.searched_artist]
        artist_url =result_artists_df['uri'][0]

        return result_artists_df, artist_url

    def _get_top_songs(self):
        '''
        Get top 10 songs of searched Artist. 

        return top_song_df: pd.DataFrame
        '''


        
        results = self.spotify.artist_top_tracks(self.artist_url)


        top_song_list = []
        for track in results['tracks'][:10]:
            top_song_list.append({'track': track['name'], 
                                  'popularity': track['popularity'],
                                  'audio': track['preview_url'],     
                                  'cover art': track['album']['images'][0]['url']
                                    })
            
        top_song_df = pd.DataFrame(top_song_list)

        return top_song_df

    def _get_all_albums(self):
        '''
        Get all albums of Searched Artist
        '''
        album_result = self.spotify.artist_albums(self.artist_url)

        album_dic_list = []
        for album in album_result['items']:
            album_dic_list.append({"name":album["name"],
                                            "release_date":album["release_date"],
                                            "total_tracks":album["total_tracks"],
                                                "album_group":album["album_group"],
                                                "album_type":album["album_type"],
                                                "artists":album["artists"][0]['external_urls']['spotify'],
                                                "available_markets":album["available_markets"],
                                                "external_urls":album["external_urls"]['spotify'],
                                                "href":album["href"],
                                                "id":album["id"],
                                                "images":album["images"],
                                                "release_date_precision":album["release_date_precision"],
                                                "type":album["type"],
                                                "uri":album["uri"]
            })
            
        all_albums_df = pd.DataFrame(album_dic_list)

        return all_albums_df


    def _get_all_songs(self, all_albums_df):
        '''
        Get all songs of Searched Artist
        '''
        
        all_album_ids = list(all_albums_df['id'])

        album_tracks_df_list = []
        for album_id in all_album_ids:
            album_track_result = self.spotify.album_tracks(album_id, limit=50, offset=0, market=None)
            track_list = []
            for track in album_track_result['items']:        
                track_list.append({"name":track["name"],
                                        "track_number":track["track_number"],
                                        "id":track["id"],
                                            "artists":track["artists"],
                                            "available_markets":track["available_markets"],
                                            "disc_number":track["disc_number"],
                                            "duration_ms":track["duration_ms"],
                                            "explicit":track["explicit"],
                                            "external_urls":track["external_urls"],
                                            "href":track["href"],
                                            "is_local":track["is_local"],
                                            "preview_url":track["preview_url"],
                                            "type":track["type"],
                                            "uri":track["uri"] })

            single_album_tracks_df = pd.DataFrame(track_list)
            album_tracks_df_list.append(single_album_tracks_df)

        all_songs_df = pd.concat(album_tracks_df_list)

        all_song_general_info_df = self._get_all_songs_general_informations(all_songs_df)
        all_song_general_info_df = self._remove_duplicated_tracks_wrapper(all_song_general_info_df, mode = 'find_top_popularity_among_tracks')

        all_song_feature_df = self._get_all_songs_with_audio_features(all_songs_df)
        all_song_feature_df = self._remove_duplicated_tracks_wrapper(all_song_feature_df, mode = 'remove_outlier')


        return all_song_general_info_df, all_song_feature_df

    def _get_all_songs_general_informations(self, all_songs_df):
        all_song_general_info_df_list = []

        limit_at_once = 50
        for n in range(1, int(len(all_songs_df)/limit_at_once)+2):
            if n!=1:
                start_index = limit_at_once*(n-1)
                end_index = limit_at_once*n
            else:
                start_index = 0
                end_index = limit_at_once
            
            song_info_result = self.spotify.tracks(list(all_songs_df['id'][start_index:end_index]))
            
            track_info_list = []
            for idx, track in enumerate(song_info_result['tracks']):
                track_info = {'name': track['name'],
                            'popularity': track['popularity'],
                            'artists': track['artists'][0]['external_urls']['spotify'],
                            'available_markets': track['available_markets'],
                            'disc_number': track['disc_number'],
                            'explicit': track['explicit'],
                            'external_ids': track['external_ids']['isrc'],
                            'href': track['href'],
                            'id': track['id'],
                            'is_local': track['is_local'],
                            'preview_url': track['preview_url'],
                            'track_number': track['track_number'],
                            'type': track['type'],
                            'uri': track['uri']
                            }
                track_info_list.append(track_info)
            track_info_df = pd.DataFrame(track_info_list)
            all_song_general_info_df_list.append(track_info_df)
            
        all_song_general_info_df = pd.concat(all_song_general_info_df_list)

        return all_song_general_info_df

    def _get_all_songs_with_audio_features(self, all_songs_df):
        '''
        Get all songs with audio features
        '''

        all_song_feature_df_list = []

        for n in range(1, int(len(all_songs_df)/100)+2):
            if n!=1:
                start_index = 100*(n-1)
                end_index = 100*n
            else:
                start_index = 0
                end_index = 100
            
            song_feat_result = self.spotify.audio_features(list(all_songs_df['id'][start_index:end_index]))
            song_feat_result_df = pd.DataFrame(song_feat_result)
            song_feat_result_df.insert(0, 'name', list(all_songs_df['name'][start_index:end_index]))
                
            all_song_feature_df_list.append(song_feat_result_df)
            
        all_song_feature_df = pd.concat(all_song_feature_df_list)

        return all_song_feature_df

    def _check_outlier(self, row, threshold):
        n_outliers = len([value for value in row.values if abs(value)>1 ])

        if n_outliers > threshold:
            return False
        else:
            return True

    def standard_scaling(self, data):
        scaler = StandardScaler()
        scaler.fit(data)
        scaled_df = pd.DataFrame(scaler.transform(data))

        return scaled_df


    def _find_top_popularity_among_same_tracks(self, duplicated_tracks_df):
        duplicated_tracks_df = duplicated_tracks_df.copy()
        top_popularity_df = duplicated_tracks_df[duplicated_tracks_df['popularity']==duplicated_tracks_df['popularity'].max()].reset_index(drop=True).iloc[0]
        
        return top_popularity_df

    def _remove_outlier(self, track_df):
        track_df = track_df.copy()

        # Drop unnecessary categorical columns 
        track_df = track_df.drop(['type', 'id', 'uri', 'track_href', 'analysis_url'], axis=1)  

        track_df = track_df.reset_index(drop = True)
        # Scaling values and see value distribution among those duplicated tracks.
        data = track_df[track_df.columns[1:]]
        scaled_df = self.standard_scaling(data)
        scaled_df.columns = track_df.columns[1:]

        # Define Threshold 
        threshold = len(scaled_df.columns)/2

        # Get index of non-outlier tracks
        non_outlier_index = scaled_df.apply(lambda x: self._check_outlier(x, threshold), axis=1)

        cleaned_track_df = track_df[non_outlier_index]
        cleaned_track_df = cleaned_track_df.groupby(['name']).mean().reset_index()

        return cleaned_track_df


    def _remove_duplicated_tracks_wrapper(self, songs_df, mode = 'remove_outlier'):
        songs_df = songs_df.copy()
           

        # Get duplicated tracks and counts
        track_count_df = songs_df['name'].value_counts().to_frame().reset_index()
        track_count_df_duplicates = track_count_df[track_count_df['name']>1]
        duplicated_tracks = list(track_count_df_duplicates['index'].unique())


        # Separate original df into non_duplicated_tracks and duplicated_tracks df
        not_duplcated_tracks_df = songs_df[~songs_df['name'].isin(duplicated_tracks)]

        duplicated_tracks_df = songs_df[songs_df['name'].isin(duplicated_tracks)]

        if mode == 'find_top_popularity_among_tracks':
            # For duplicated track, it will remove outlier 
            removed_duplicated_tracks_df= duplicated_tracks_df.groupby(['name']).apply(lambda x:self._find_top_popularity_among_same_tracks(x))

        elif mode == 'remove_outlier':
            # For duplicated track, it will remove outlier  
            removed_duplicated_tracks_df = duplicated_tracks_df.groupby(['name']).apply(lambda x:self._remove_outlier(x))

            # Drop unnecessary categorical columns 
            not_duplcated_tracks_df = not_duplcated_tracks_df.drop(['type', 'id', 'uri', 'track_href', 'analysis_url'], axis=1)  

        # Re-merge two dataframe to make it original 
        cleaned_tracks_df = pd.concat([not_duplcated_tracks_df, removed_duplicated_tracks_df]).reset_index(drop = True)

        return cleaned_tracks_df


    def filter_by_popularity(self, n_top_tracks = 100):
        unique_tracks_feat_df = self.all_song_feature_df.copy()
        tracks_gen_df = self.all_song_general_info_df.copy()

        top_tracks_df = tracks_gen_df.sort_values(by = 'popularity', ascending=False).head(n_top_tracks).reset_index(drop=True)

        filtered_top_tracks_df = unique_tracks_feat_df[unique_tracks_feat_df['name'].isin(top_tracks_df['name'])].reset_index(drop=True)

        return filtered_top_tracks_df




    











