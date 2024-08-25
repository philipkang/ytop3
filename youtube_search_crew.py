import os
import streamlit as st
from googleapiclient.discovery import build
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Streamlit app title
st.title("YouTube Video Search and Analysis")

# Input for YouTube API Key
youtube_api_key = st.text_input("Enter your YouTube API Key", type="password")
os.environ['YOUTUBE_API_KEY'] = youtube_api_key

# Input for OpenAI API Key
openai_api_key = st.text_input("Enter your OpenAI API Key", type="password")
os.environ['OPENAI_API_KEY'] = openai_api_key

# Input for search topic
topic = st.text_input("Enter the topic to search for YouTube videos")

def fallback_youtube_search(query):
    url = f"https://www.youtube.com/results?search_query={query}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    videos = []
    for video in soup.select('.yt-uix-tile-link')[:10]:
        if video['href'].startswith('/watch?v='):
            title = video['title']
            link = f"https://www.youtube.com{video['href']}"
            videos.append({'title': title, 'link': link})
    return videos

def search_youtube_videos(topic):
    try:
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        search_response = youtube.search().list(
            q=topic,
            type='video',
            part='id,snippet',
            maxResults=10
        ).execute()

        videos = []
        for item in search_response['items']:
            video_id = item['id']['videoId']
            channel_id = item['snippet']['channelId']

            # Get channel statistics
            channel_response = youtube.channels().list(
                part='statistics',
                id=channel_id
            ).execute()

            subscribers = channel_response['items'][0]['statistics']['subscriberCount'] if channel_response['items'] else 'N/A'

            # Get video statistics
            video_response = youtube.videos().list(
                part='statistics',
                id=video_id
            ).execute()

            view_count = video_response['items'][0]['statistics']['viewCount'] if video_response['items'] else 'N/A'

            video = {
                'title': item['snippet']['title'],
                'channel': item['snippet']['channelTitle'],
                'subscribers': subscribers,
                'views': view_count,
                'date': item['snippet']['publishedAt'],
                'link': f"https://www.youtube.com/watch?v={video_id}"
            }
            videos.append(video)

        return videos
    except Exception as e:
        logging.error(f"Error in YouTube API search: {str(e)}")
        logging.info("Falling back to web scraping method")
        return fallback_youtube_search(topic)

def analyze_videos(videos, topic):
    client = OpenAI(api_key=openai_api_key)
    
    prompt = f"""Analyze the following list of YouTube videos related to the topic '{topic}':

{videos}

Select the top 3 unique videos that are most relevant to the topic '{topic}'. Consider the following criteria:
1. The video title should closely match the topic.
2. Prioritize channels with high subscriber counts (preferably over 100,000 subscribers).
3. Consider view count and recency as secondary factors.
4. Ensure no two videos are from the same channel.

For each selected video, provide the following information:
1. Title (with link)
2. Channel name
3. Subscriber count
4. View count
5. Publication date

Present the results in a clear, formatted manner."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that analyzes YouTube video search results."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content

# Button to start the search
if st.button("Search and Analyze"):
    if not youtube_api_key or not openai_api_key:
        st.error("Please enter both YouTube and OpenAI API keys.")
    elif not topic:
        st.error("Please enter a topic to search for.")
    else:
        with st.spinner("Searching and analyzing videos..."):
            try:
                videos = search_youtube_videos(topic)
                result = analyze_videos(videos, topic)
                st.success("Search and analysis complete!")
                st.markdown(result)
            except Exception as e:
                logging.error(f"Error during execution: {str(e)}")
                st.error(f"An error occurred: {str(e)}")
                st.info("Please try again or check the logs for more information.")
