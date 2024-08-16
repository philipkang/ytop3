import os
import streamlit as st
from crewai import Agent, Task, Crew, Process
from langchain.tools import Tool
from googleapiclient.discovery import build
from langchain_openai import OpenAI

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

# Button to start the search
if st.button("Search and Analyze"):
    if not youtube_api_key or not openai_api_key:
        st.error("Please enter both YouTube and OpenAI API keys.")
    elif not topic:
        st.error("Please enter a topic to search for.")
    else:
        with st.spinner("Searching and analyzing videos..."):
            try:
                youtube = build('youtube', 'v3', developerKey=youtube_api_key)
                llm = OpenAI(temperature=0.1, openai_api_key=openai_api_key, model="gpt-4-mini")

                def search_youtube_videos(topic):
                    try:
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
                        return f"Error occurred while searching: {str(e)}"

                youtube_search_tool = Tool(
                    name="YouTube Search",
                    func=search_youtube_videos,
                    description="Search for YouTube videos on a given topic related to Generative AI and Large Language Model"
                )

                youtube_search_agent = Agent(
                    role='YouTube Search Agent',
                    goal='Find the most relevant YouTube videos for the given topic, ensuring close match with key words.',
                    verbose=True,
                    allow_delegation=False,
                    backstory=(
                        "You are an expert in finding the most relevant YouTube videos based on the exact topic provided. "
                        "You focus on videos whose titles closely match the key words in the given topic, "
                        "especially in the context of Generative AI and LLM development. If the search fails, you provide clear instructions for manual search."
                    ),
                    tools=[youtube_search_tool]
                )

                video_analyst = Agent(
                    role='Video Analyst',
                    goal='Analyze the list of YouTube videos and pick the top 3 unique matches that are most relevant to the exact topic, ensuring no videos are from the same channel and prioritizing channels with high subscriber counts.',
                    verbose=True,
                    allow_delegation=False,
                    backstory=(
                        "You excel in analyzing video content relevance and channel popularity. You carefully evaluate video titles to ensure "
                        "they closely match the given topic. You prioritize videos that specifically mention key words from the topic "
                        "and come from channels with high subscriber counts (preferably over 100,000 subscribers). "
                        "You also consider recency and view count as secondary factors. "
                        "You ensure that there are no duplicate entries in your final selection and that no two videos are from the same channel. "
                        "If given instructions for manual search, you explain how to analyze the results. "
                        "When presenting your final selection, use the following format for each video:\n"
                        "1. **Title:** [Video Title](Video URL)\n"
                        "   - **Channel:** Channel Name\n"
                        "   - **Subscribers:** Subscriber Count\n"
                        "   - **Views:** View Count\n"
                        "   - **Publication Date:** Publication Date\n"
                        "   - **Video Url:** Url Link\n\n"
                    )
                )

                search_task = Task(
                    description=(
                        f"Search YouTube for videos that closely match the topic '{topic}'. "
                        "Ensure the video titles contain key words from the topic. "
                        "Provide a list of videos including their titles, channels, subscriber numbers, view counts, "
                        "publication dates, and video link URLs. If the search fails, provide clear instructions for manual search."
                    ),
                    expected_output='A list of YouTube videos with title, channel name, subscriber count, view count, publication date and video url link, ensuring close match to the topic. Or instructions for manual search if automated search fails.',
                    agent=youtube_search_agent
                )

                analyze_task = Task(
                    description=(
                        f"Review the list of YouTube videos provided or the manual search instructions. If given a list, select the top 3 unique videos whose titles "
                        f"most closely match the topic '{topic}'. Prioritize videos that specifically mention "
                        "key words from the topic and come from channels with high subscriber counts (preferably over 100,000 subscribers). "
                        "Consider recency and view count as secondary factors. "
                        "Ensure there are no duplicates in your final selection and that no two videos are from the same channel. "
                        "Present each video only once in your output, including the view count for each video. "
                        "If given manual search instructions, explain how to analyze the results."
                    ),
                    expected_output='A list of the top 3 unique YouTube videos most relevant to the topic, with their titles, channel names, subscriber counts (prioritizing channels with over 100,000 subscribers), view counts, publication dates, and video url links. Each video should appear only once, and no two videos should be from the same channel. Or an explanation of how to analyze manual search results.',
                    agent=video_analyst
                )

                crew = Crew(
                    agents=[youtube_search_agent, video_analyst],
                    tasks=[search_task, analyze_task],
                    process=Process.sequential
                )

                result = crew.kickoff()
                st.success("Search and analysis complete!")
                st.markdown(result)

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")