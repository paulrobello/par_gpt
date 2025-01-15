import re
from pathlib import Path

from dotenv import load_dotenv
from par_ai_core.par_logging import console_err
from RealtimeSTT import AudioToTextRecorder
from rich.console import Console


class VoiceInputManager:
    def __init__(
        self,
        wake_word: str = "GPT",
        *,
        model: str = "small.en",
        post_speech_silence_duration: float = 1.5,
        batch_size: int = 25,
        verbose: bool = False,
        console: Console | None = None,
    ):
        self.console = console or console_err
        self.verbose = verbose
        self.model = model
        self.post_speech_silence_duration = post_speech_silence_duration
        self.recorder: AudioToTextRecorder | None = None
        self.batch_size = batch_size
        self.wake_word = wake_word
        self.last_transcript = ""

    def init_recorder(self):
        self.recorder = AudioToTextRecorder(
            spinner=False,
            # realtime_processing_pause=0.3,
            post_speech_silence_duration=self.post_speech_silence_duration,
            # post_speech_silence_duration=1.5,  # how long to wait after speech ends before processing
            # compute_type="int8",
            compute_type="float32",
            model=self.model,
            # model="tiny.en",  # VERY fast (.5s), but not accurate
            # model="small.en",  # decent speed (1.5s), improved accuracy
            # Beam size controls how many alternative transcription paths are explored
            # Higher values = more accurate but slower, lower values = faster but less accurate
            # beam_size=3,
            # beam_size=5,
            beam_size=8,
            # Batch size controls how many audio chunks are processed together
            # Higher values = faster processing but uses more memory, lower values = slower processing but uses less memory
            # batch_size=25,
            batch_size=self.batch_size,
            # model="large-v3",  # very slow, but accurate
            # model="distil-large-v3", # very slow (but faster than large-v3) but accurate
            # realtime_model_type="tiny.en", # realtime models are used for the on_realtime_transcription_update() callback
            # realtime_model_type="large-v3",
            language="en",
            print_transcription_time=self.verbose,
            # enable_realtime_transcription=True,
            # on_realtime_transcription_update=lambda text: print(
            #     f"🎤 on_realtime_transcription_update(): {text}"
            # ),
            # on_realtime_transcription_stabilized=lambda text: print(
            #     f"🎤 on_realtime_transcription_stabilized(): {text}"
            # ),
            # on_recorded_chunk=lambda chunk: print(f"🎤 on_recorded_chunk(): {chunk}"),
            # on_transcription_start=lambda: print("🎤 on_transcription_start()"),
            # on_recording_stop=lambda: print("🎤 on_transcription_stop()"),
            # on_recording_start=lambda: print("🎤 on_recording_start()"),
        )

    def process_text(self, text: str) -> str:
        if not text:
            return ""
        try:
            if self.verbose:
                console_err.print(f"\n🎤 Heard: {text}")

            matches = re.findall(rf"(?i)\b({self.wake_word})\b(.*)", text)
            if not matches:
                if self.verbose:
                    console_err.print(f"🤖 Not {self.wake_word} - ignoring")
                return ""
            if self.recorder:
                self.recorder.stop()

            text = matches[0][1].strip(" \t,.?!\"'")
            if self.verbose:
                console_err.print(f"🎤 USING: {text}")
            return text
        except Exception as e:
            console_err.print(f"❌ Voice Input Error: {str(e)}")
            return ""

    def get_text(self) -> str:
        self.last_transcript = ""
        if not self.recorder:
            self.init_recorder()
        else:
            self.recorder.start()
        console_err.print(f"🎤 Listening for name '{self.wake_word}'. Say '{self.wake_word} exit' to stop listening.")
        while self.recorder is not None:
            self.last_transcript = self.process_text(self.recorder.text() or "")
            if self.last_transcript:
                return self.last_transcript

        return ""

    def shutdown(self):
        if self.recorder:
            self.recorder.shutdown()


if __name__ == "__main__":
    load_dotenv(Path("~/.par_gpt.env").expanduser())
    # console_err.print(re.findall(rf"(?i)\b({assistant_name})\b(.*)", "GP what is the weather?"))
    # console_err.print(re.findall(rf"(?i)\b({assistant_name})\b(.*)", "GPT what is the weather?"))
    # console_err.print(re.findall(rf"(?i)\b({assistant_name})\b(.*)", "GPT, what is the weather?"))
    # console_err.print(re.findall(rf"(?i)\b({assistant_name})\b(.*)", "today is a good day. GPT, what is the weather?"))
    # console_err.print(re.findall(rf"(?i)\b({assistant_name})\b(.*)", "GPT today is a good day. GPTME, what is the weather?"))
    # exit(0)
    voice_input_manager = VoiceInputManager(verbose=True)
    while True:
        text = voice_input_manager.get_text()
        console_err.print(text)
        if text.lower() == "exit":
            break
    voice_input_manager.shutdown()
