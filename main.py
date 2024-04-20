import re
import g4f
import json
import time
import requests
import assemblyai as aai

from utils import *
from cache import *
from Tts import TTS
from config import *
from status import *
from uuid import uuid4
from constants import *
from typing import List
from moviepy.editor import *
from termcolor import colored
# from selenium_firefox import *
# from selenium import webdriver
from moviepy.video.fx.all import crop
from moviepy.config import change_settings
# from selenium.webdriver.common.by import By
# from selenium.webdriver.firefox.service import Service
# from selenium.webdriver.firefox.options import Options
from moviepy.video.tools.subtitles import SubtitlesClip
# from webdriver_manager.firefox import GeckoDriverManager
from datetime import datetime

# Set ImageMagick Path
change_settings({"IMAGEMAGICK_BINARY": get_imagemagick_path()})


class YouTube:
    """
    Class for YouTube Automation.

    Steps to create a YouTube Short:
    1. Generate a topic [DONE]
    2. Generate a script [DONE]
    3. Generate metadata (Title, Description, Tags) [DONE]
    4. Generate AI Image Prompts [DONE]
    4. Generate Images based on generated Prompts [DONE]
    5. Convert Text-to-Speech [DONE]
    6. Show images each for n seconds, n: Duration of TTS / Amount of images [DONE]
    7. Combine Concatenated Images with the Text-to-Speech [DONE]
    """
    def __init__(self, niche: str, language: str) -> None:
        """
        Constructor for YouTube Class.

        Args:
            account_uuid (str): The unique identifier for the YouTube account.
            account_nickname (str): The nickname for the YouTube account.
            fp_profile_path (str): Path to the firefox profile that is logged into the specificed YouTube Account.
            niche (str): The niche of the provided YouTube Channel.
            language (str): The language of the Automation.

        Returns:
            None
        """
        self._niche: str = niche
        self._language: str = language

        self.images = []

        # Initialize the Firefox profile
        # self.options: Options = Options()
        
        # # Set headless state of browser
        # if get_headless():
        #     self.options.add_argument("--headless")

        # # Set the profile path
        # self.options.add_argument("-profile")
        # self.options.add_argument(fp_profile_path)

        # Set the service
        # self.service: Service = Service(GeckoDriverManager().install())

        # Initialize the browser
        # self.browser: webdriver.Firefox = webdriver.Firefox(service=self.service, options=self.options)

    @property
    def niche(self) -> str:
        """
        Getter Method for the niche.

        Returns:
            niche (str): The niche
        """
        return self._niche
    
    @property
    def language(self) -> str:
        """
        Getter Method for the language to use.

        Returns:
            language (str): The language
        """
        return self._language
    
    def generate_response(self, prompt: str, model: any = None) -> str:
        """
        Generates an LLM Response based on a prompt and the user-provided model.

        Args:
            prompt (str): The prompt to use in the text generation.

        Returns:
            response (str): The generated AI Repsonse.
        """
        if not model:
            return g4f.ChatCompletion.create(
                model=parse_model(get_model()),
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
        else:
            return g4f.ChatCompletion.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

    def generate_topic(self) -> str:
        """
        Generates a topic based on the YouTube Channel niche.

        Returns:
            topic (str): The generated topic.
        """
        completion = self.generate_response(f"Please generate a specific video idea that takes about the following topic: {self.niche}. Make it exactly one sentence. Only return the topic, nothing else.")

        if not completion:
            error("Failed to generate Topic.")

        self.subject = completion

        return completion

    def generate_script(self) -> str:
        """
        Generate a script for a video, depending on the subject of the video, the number of paragraphs, and the AI model.

        Returns:
            script (str): The script of the video.
        """
        prompt = f"""
        Generate a script for a video in 4 sentences, depending on the subject of the video.

        The script is to be returned as a string with the specified number of paragraphs.

        Here is an example of a string:
        "This is an example string."

        Do not under any circumstance reference this prompt in your response.

        Get straight to the point, don't start with unnecessary things like, "welcome to this video".

        Obviously, the script should be related to the subject of the video.
        
        YOU MUST NOT EXCEED THE 4 SENTENCES LIMIT. MAKE SURE THE 4 SENTENCES ARE SHORT.
        YOU MUST NOT INCLUDE ANY TYPE OF MARKDOWN OR FORMATTING IN THE SCRIPT, NEVER USE A TITLE.
        YOU MUST WRITE THE SCRIPT IN THE LANGUAGE SPECIFIED IN [LANGUAGE].
        ONLY RETURN THE RAW CONTENT OF THE SCRIPT. DO NOT INCLUDE "VOICEOVER", "NARRATOR" OR SIMILAR INDICATORS OF WHAT SHOULD BE SPOKEN AT THE BEGINNING OF EACH PARAGRAPH OR LINE. YOU MUST NOT MENTION THE PROMPT, OR ANYTHING ABOUT THE SCRIPT ITSELF. ALSO, NEVER TALK ABOUT THE AMOUNT OF PARAGRAPHS OR LINES. JUST WRITE THE SCRIPT
        
        Subject: {self.subject}
        Language: {self.language}
        """
        completion = self.generate_response(prompt)

        # Apply regex to remove *
        completion = re.sub(r"\*", "", completion)
        
        if not completion:
            error("The generated script is empty.")
            return
        
        if len(completion) > 5000:
            if get_verbose():
                warning("Generated Script is too long. Retrying...")
            self.generate_script()
        
        self.script = completion
    
        return completion

    def generate_metadata(self) -> dict:
        """
        Generates Video metadata for the to-be-uploaded YouTube Short (Title, Description).

        Returns:
            metadata (dict): The generated metadata.
        """
        title = self.generate_response(f"Please generate a YouTube Video Title for the following subject, including hashtags: {self.subject}. Only return the title, nothing else. Limit the title under 100 characters.")

        if len(title) > 100:
            if get_verbose():
                warning("Generated Title is too long. Retrying...")
            return self.generate_metadata()

        description = self.generate_response(f"Please generate a YouTube Video Description for the following script: {self.script}. Only return the description, nothing else.")
        
        self.metadata = {
            "title": title,
            "description": description
        }

        return self.metadata
    
    def generate_prompts(self) -> List[str]:
        """
        Generates AI Image Prompts based on the provided Video Script.

        Returns:
            image_prompts (List[str]): Generated List of image prompts.
        """
        n_prompts = len(self.script) / 3

        prompt = f"""
        Generate {n_prompts} Image Prompts for AI Image Generation,
        depending on the subject of a video.
        Subject: {self.subject}

        The image prompts are to be returned as
        a JSON-Array of strings.

        Each search term should consist of a full sentence,
        always add the main subject of the video.

        Be emotional and use interesting adjectives to make the
        Image Prompt as detailed as possible.
        
        YOU MUST ONLY RETURN THE JSON-ARRAY OF STRINGS.
        YOU MUST NOT RETURN ANYTHING ELSE. 
        YOU MUST NOT RETURN THE SCRIPT.
        
        The search terms must be related to the subject of the video.
        Here is an example of a JSON-Array of strings:
        ["image prompt 1", "image prompt 2", "image prompt 3"]

        For context, here is the full text:
        {self.script}
        """

        completion = str(self.generate_response(prompt, model=parse_model(get_image_prompt_llm())))\
            .replace("```json", "") \
            .replace("```", "")

        image_prompts = []

        if "image_prompts" in completion:
            image_prompts = json.loads(completion)["image_prompts"]
        else:
            try:
                image_prompts = json.loads(completion)
                if get_verbose():
                    info(f" => Generated Image Prompts: {image_prompts}")
            except Exception:
                if get_verbose():
                    warning("GPT returned an unformatted response. Attempting to clean...")

                # Get everything between [ and ], and turn it into a list
                r = re.compile(r"\[.*\]")
                image_prompts = r.findall(completion)
                if len(image_prompts) == 0:
                    if get_verbose():
                        warning("Failed to generate Image Prompts. Retrying...")
                    return self.generate_prompts()

        self.image_prompts = image_prompts

        # Check the amount of image prompts
        # and remove if it's more than needed
        if len(image_prompts) > n_prompts:
            image_prompts = image_prompts[:n_prompts]

        success(f"Generated {len(image_prompts)} Image Prompts.")

        return image_prompts

    def generate_image(self, prompt: str) -> str:
        """
        Generates an AI Image based on the given prompt.

        Args:
            prompt (str): Reference for image generation

        Returns:
            path (str): The path to the generated image.
        """
        ok = False
        while ok == False:
            url = f"https://hercai.onrender.com/{get_image_model()}/text2image?prompt={prompt}"

            r = requests.get(url)
            parsed = r.json()

            if "url" not in parsed or not parsed.get("url"):
                # Retry
                if get_verbose():
                    info(f" => Failed to generate Image for Prompt: {prompt}. Retrying...")
                ok = False
            else:
                ok = True
                image_url = parsed["url"]

                if get_verbose():
                    info(f" => Generated Image: {image_url}")

                image_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".png")
                
                with open(image_path, "wb") as image_file:
                    # Write bytes to file
                    image_r = requests.get(image_url)

                    image_file.write(image_r.content)

                if get_verbose():
                    info(f" => Wrote Image to \"{image_path}\"\n")

                self.images.append(image_path)
                
                return image_path

    def generate_script_to_speech(self, tts_instance: TTS) -> str:
        """
        Converts the generated script into Speech using CoquiTTS and returns the path to the wav file.

        Args:
            tts_instance (tts): Instance of TTS Class.

        Returns:
            path_to_wav (str): Path to generated audio (WAV Format).
        """
        path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".wav")

        # Clean script, remove every character that is not a word character, a space, a period, a question mark, or an exclamation mark.
        self.script = re.sub(r'[^\w\s.?!]', '', self.script)

        tts_instance.synthesize(self.script, path)

        self.tts_path = path

        if get_verbose():
            info(f" => Wrote TTS to \"{path}\"")

        return path
    

    def generate_subtitles(self, audio_path: str) -> str:
        """
        Generates subtitles for the audio using AssemblyAI.

        Args:
            audio_path (str): The path to the audio file.

        Returns:
            path (str): The path to the generated SRT File.
        """
        # Turn the video into audio
        aai.settings.api_key = get_assemblyai_api_key()
        config = aai.TranscriptionConfig()
        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(audio_path)
        subtitles = transcript.export_subtitles_srt()

        srt_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".srt")

        with open(srt_path, "w") as file:
            file.write(subtitles)

        return srt_path

    def combine(self) -> str:
        """
        Combines everything into the final video.

        Returns:
            path (str): The path to the generated MP4 File.
        """
        combined_image_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")
        threads = get_threads()
        tts_clip = AudioFileClip(self.tts_path)
        max_duration = tts_clip.duration
        req_dur = max_duration / len(self.images)

        # Make a generator that returns a TextClip when called with consecutive
        generator = lambda txt: TextClip(
            txt,
            font=os.path.join(get_fonts_dir(), get_font()),
            fontsize=100,
            color="#FFFF00",
            stroke_color="black",
            stroke_width=5,
            size=(1080, 1920),
            method="caption",
        )

        print(colored("[+] Combining images...", "blue"))

        clips = []
        tot_dur = 0
        # Add downloaded clips over and over until the duration of the audio (max_duration) has been reached
        while tot_dur < max_duration:
            for image_path in self.images:
                clip = ImageClip(image_path)
                clip.duration = req_dur
                clip = clip.set_fps(30)

                # Not all images are same size,
                # so we need to resize them
                if round((clip.w/clip.h), 4) < 0.5625:
                    if get_verbose():
                        info(f" => Resizing Image: {image_path} to 1080x1920")
                    clip = crop(clip, width=clip.w, height=round(clip.w/0.5625), \
                                x_center=clip.w / 2, \
                                y_center=clip.h / 2)
                else:
                    if get_verbose():
                        info(f" => Resizing Image: {image_path} to 1920x1080")
                    clip = crop(clip, width=round(0.5625*clip.h), height=clip.h, \
                                x_center=clip.w / 2, \
                                y_center=clip.h / 2)
                clip = clip.resize((1080, 1920))

                # FX (Fade In)
                #clip = clip.fadein(2)

                clips.append(clip)
                tot_dur += clip.duration

        final_clip = concatenate_videoclips(clips)
        final_clip = final_clip.set_fps(30)
        random_song = choose_random_song()
        
        subtitles_path = self.generate_subtitles(self.tts_path)

        # Equalize srt file
        equalize_subtitles(subtitles_path, 10)
        
        # Burn the subtitles into the video
        subtitles = SubtitlesClip(subtitles_path, generator)

        subtitles.set_pos(("center", "center"))
        random_song_clip = AudioFileClip(random_song).set_fps(44100)

        # Turn down volume
        random_song_clip = random_song_clip.fx(afx.volumex, 0.1)
        comp_audio = CompositeAudioClip([
            tts_clip.set_fps(44100),
            random_song_clip
        ])

        final_clip = final_clip.set_audio(comp_audio)
        final_clip = final_clip.set_duration(tts_clip.duration)

        # Add subtitles
        final_clip = CompositeVideoClip([
            final_clip,
            subtitles
        ])

        final_clip.write_videofile(combined_image_path, threads=threads)

        success(f"Wrote Video to \"{combined_image_path}\"")

        return combined_image_path

    def generate_video(self, tts_instance: TTS) -> str:
        """
        Generates a YouTube Short based on the provided niche and language.

        Args:
            tts_instance (TTS): Instance of TTS Class.

        Returns:
            path (str): The path to the generated MP4 File.
        """
        # Generate the Topic
        self.generate_topic()

        # Generate the Script
        self.generate_script()

        # Generate the Metadata
        # self.generate_metadata()

        # Generate the Image Prompts
        self.generate_prompts()

        # Generate the Images
        for prompt in self.image_prompts:
            self.generate_image(prompt)

        # Generate the TTS
        self.generate_script_to_speech(tts_instance)

        # Combine everything
        path = self.combine()

        if get_verbose():
            info(f" => Generated Video: {path}")

        self.video_path = os.path.abspath(path)

        return path
    
    
tts = TTS()
youtube = YouTube(
                    "motivation and sports",
                    "english"
                )

youtube.generate_video(tts)