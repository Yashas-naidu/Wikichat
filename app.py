import streamlit as st
import google.generativeai as genai
import os
import shutil
import cv2
import wikipedia
from wikipedia.exceptions import DisambiguationError, PageError
import textwrap
import numpy as np
from PIL import Image
import io
import glob
import wikipedia
from wikipedia.exceptions import DisambiguationError, PageError
from IPython.display import Markdown

genai.configure(api_key="AIzaSyDizqsziEBf2KPn11HMBGdavSFtVLbKhrQ")
model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")




FRAME_EXTRACTION_DIRECTORY = r"C:\Users\YASHAS\Mu-Llama\Frames"
FRAME_PREFIX = "_frame"

def create_frame_output_dir(output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        shutil.rmtree(output_dir)
        os.makedirs(output_dir)

def extract_frame_from_video(video_file_path):
    print(f"Extracting {video_file_path} at 1 frame per second. This might take a bit...")
    create_frame_output_dir(FRAME_EXTRACTION_DIRECTORY)
    vidcap = cv2.VideoCapture(video_file_path)
    fps = vidcap.get(cv2.CAP_PROP_FPS)
    frame_duration = 1 / fps  # Time interval between frames (in seconds)
    output_file_prefix = os.path.basename(video_file_path).replace('.', '_')
    frame_count = 0
    count = 0
    while vidcap.isOpened():
        success, frame = vidcap.read()
        if not success: # End of video
            break
        if int(count / fps) == frame_count: # Extract a frame every second
            min = frame_count // 60
            sec = frame_count % 60
            time_string = f"{min:02d}:{sec:02d}"
            image_name = f"{output_file_prefix}{FRAME_PREFIX}{time_string}.jpg"
            output_filename = os.path.join(FRAME_EXTRACTION_DIRECTORY, f"{output_file_prefix}_frame{frame_count:02d}_{sec:02d}.jpg")
            cv2.imwrite(output_filename, frame)
            print(f"Saved frame to {output_filename}")
            frame_count += 1
        count += 1
    vidcap.release() # Release the capture object\n",
    print(f"Completed video frame extraction!\n\nExtracted: {frame_count} frames")

class File:
    def __init__(self, file_path: str, display_name: str = None):
        self.file_path = file_path
        if display_name:
            self.display_name = display_name
        self.timestamp = self.get_timestamp(file_path)

    def set_file_response(self, response):
        self.response = response

    def get_timestamp(self, filename):  # Add 'self' as the first argument
        """Extracts the frame count (as an integer) from a filename with the format
            'output_file_prefix_frame00:00.jpg'.
        """
        parts = filename.split(FRAME_PREFIX)
        if len(parts) != 2:
            return None  # Indicates the filename might be incorrectly formatted
        return parts[1].split('.')[0]

def to_markdown(text):
    text = text.replace('•', '  *')
    return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))

# Function to search Wikipedia and summarize relevant documents
def wikipedia_search(search_queries, n_topics):
    search_history = set()  # tracking search history
    search_urls = []
    summary_results = []

    for query in search_queries:
        st.write(f'Searching for "{query}"')
        search_terms = wikipedia.search(query)
        st.write(f"Related search terms: {search_terms[:n_topics]}")

        for search_term in search_terms[:n_topics]:  # select first `n_topics` candidates
            if search_term in search_history:  # check if the topic is already covered
                continue

            st.write(f'Fetching page: "{search_term}"')
            search_history.add(search_term)  # add to search history

            try:
                # extract the relevant data by using GenerativeAI model
                page = wikipedia.page(search_term, auto_suggest=False)
                url = page.url
                st.write(f"Information Source: {url}")
                search_urls.append(url)
                page_content = page.content

                response = model.generate_content(textwrap.dedent(f"""
                    Extract relevant information about user's query: {query}
                    From this source:
                    {page_content}
                    Note: Do not summarize. Only Extract and return the relevant information
                """))

                urls = [url]

                if response.candidates[0].citation_metadata:
                    extra_citations = response.candidates[0].citation_metadata.citation_sources
                    extra_urls = [source.uri for source in extra_citations]  # Changed attribute name to 'uri'
                    urls.extend(extra_urls)
                    search_urls.extend(extra_urls)
                    st.write("Additional citations:", response.candidates[0].citation_metadata.citation_sources)

                try:
                    text = response.text
                except ValueError:
                    pass
                else:
                    summary_results.append(text + "\n\nBased on:\n  " + ',\n  '.join(urls))
            except DisambiguationError:
                st.write(f"""Results when searching for "{search_term}" (originally for "{query}") were ambiguous, hence skipping""")
            except PageError:
                st.write(f'{search_term} did not match with any page id, hence skipping.')

    st.write(f"Information Sources:")
    for url in search_urls:
        st.write('    ', url)

    return summary_results

def make_request(prompt, files):
    request = [prompt]
    for file in files:
        request.append(file.timestamp)
        request.append(file.response)
    return request

# Sidebar
# option = st.sidebar.selectbox(
#     'Which task do you want to perform?',
#     ('Audio', 'Video', 'Wiki'))
option = st.sidebar.radio(
    'Which task do you want to perform?',
    (
    # 'Audio', 'Video', 
     'Wiki',
    #  'Image'
     ))


if option == 'Audio':
    uploaded_file = st.file_uploader("Choose an audio file", type=['mp3', 'wav'])
    if uploaded_file is not None:
        file_details = {"FileName":uploaded_file.name,"FileType":uploaded_file.type,"FileSize":uploaded_file.size}
        st.write(file_details)
        audio_bytes = uploaded_file.read()
        st.audio(audio_bytes, format='audio/' + uploaded_file.type.split('/')[-1])
        # Save the uploaded file to disk
        file_path = os.path.join(os.getcwd(), 'sample.mp3')
        with open(file_path, 'wb') as f:
            f.write(audio_bytes)
        # Then upload the file to the Generative AI service
        your_file = genai.upload_file(path=file_path)
        if 'prompts' not in st.session_state:
            st.session_state.prompts = []
        prompt = st.text_input("Enter your prompt", key='unique')
        if prompt:
            model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
            response = model.generate_content([prompt, your_file], stream=True)
            response.resolve()
            st.session_state.prompts.append((prompt, response.text))
        for prompt, response in reversed(st.session_state.prompts):
            st.markdown(f'<p style="font-family:sans-serif; color:Red; font-size: 20px;"><b>Prompt:</b> {prompt}</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="font-family:sans-serif; color:White;"><b>Response:</b> {response}</p>', unsafe_allow_html=True)



elif option == 'Video':
    files = glob.glob(r'C:\Users\YASHAS\Mu-Llama\Frames\*.jpg')
    for f in files:
        os.remove(f)
    uploaded_file = st.file_uploader("Choose a video file", type=['mp4', 'mov', 'avi'])
    if uploaded_file is not None:
        file_details = {"FileName": uploaded_file.name, "FileType": uploaded_file.type, "FileSize": uploaded_file.size}
        st.write(file_details)
        video_bytes = uploaded_file.read()
        st.video(video_bytes, format='video/' + uploaded_file.type.split('/')[-1])
        video_file_path = "uploaded_video." + uploaded_file.name.split(".")[-1]
        with open(video_file_path, "wb") as f:
            f.write(video_bytes)
        # Extract frames from the uploaded video
        extract_frame_from_video(video_file_path)
        
        # Process the extracted frames and upload them
        files = os.listdir(FRAME_EXTRACTION_DIRECTORY)
        files = sorted(files)
        files_to_upload = []
        for file in files:
            files_to_upload.append(File(file_path=os.path.join(FRAME_EXTRACTION_DIRECTORY, file)))

        full_video = False  # Upload only a 10 second slice
        uploaded_files = []
        print(f'Uploading {len(files_to_upload) if full_video else 540} files. This might take a bit...')

        for file in files_to_upload if full_video else files_to_upload[30:40]:
            print(f'Uploading: {file.file_path}...')
            response = genai.upload_file(path=file.file_path)
            file.set_file_response(response)
            uploaded_files.append(file)

        print(f"Completed file uploads!\n\nUploaded: {len(uploaded_files)} files")
        
        # Generate content using Gemini 1.5 Pro model
        if 'prompts' not in st.session_state:
            st.session_state.prompts = []
        prompt = st.text_input("Enter your prompt", key='unique')
        if prompt:
            request = make_request(prompt, uploaded_files)
            response = model.generate_content(request, request_options={"timeout": 600})
            response.resolve()
            st.session_state.prompts.append((prompt, response.text))
        for prompt, response in reversed(st.session_state.prompts):
            st.markdown(f'<p style="font-family:sans-serif; color:Red; font-size: 20px;"><b>Prompt:</b> {prompt}</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="font-family:sans-serif; color:White;"><b>Response:</b> {response}</p>', unsafe_allow_html=True)
        # request = make_request(prompt, uploaded_files)
        # response = model.generate_content(request, request_options={"timeout": 600})
        # print(response.text)

        

# Wiki
elif option == 'Wiki':
    search_query = st.text_input("Enter your topic")
    n_topics = st.number_input("Enter the number of topics to search (recommended 3 for best results)", value=1, min_value=1)
    if st.button("Search"):
        if search_query:
            results = wikipedia_search([search_query], n_topics)
            for result in results:
                st.markdown(result)

elif option=='Image':
    uploaded_file = st.file_uploader("Choose an image file", type=['jpg', 'jpeg', 'png'])
    if uploaded_file is not None:
        file_details = {"FileName":uploaded_file.name,"FileType":uploaded_file.type,"FileSize":uploaded_file.size}
        st.write(file_details)
        image_bytes = uploaded_file.read()
        st.image(image_bytes, caption='Uploaded Image', use_column_width=True)
        img = Image.open(io.BytesIO(image_bytes))
        img = img.resize((512, 512))
        model = genai.GenerativeModel('gemini-pro-vision')
        if 'prompts' not in st.session_state:
            st.session_state.prompts = []
        prompt = st.text_input("Enter your prompt", key='unique')
        if prompt:
            response = model.generate_content([prompt, img], stream=True)
            response.resolve()
            st.session_state.prompts.append((prompt, response.text))
        for prompt, response in reversed(st.session_state.prompts):
            st.markdown(f'<p style="font-family:sans-serif; color:Red; font-size: 20px;"><b>Prompt:</b> {prompt}</p>', unsafe_allow_html=True)
            st.markdown(f'<p style="font-family:sans-serif; color:White;"><b>Response:</b> {response}</p>', unsafe_allow_html=True)