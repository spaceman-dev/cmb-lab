import { useEffect, useRef, useState } from "react";

interface AudioPlayerProps {
  src: string;
  fallbackText: string;
  estimatedSeconds?: number;
  available: boolean;
  label?: string;
}

/**
 * Audio explainer with a browser-speech fallback.
 *
 * Server-side synthesis (macOS `say`) gives a consistent voice and is cached, so it is
 * preferred. When the backend cannot synthesise — Linux, CI — we fall back to the
 * browser's SpeechSynthesis API so the feature degrades instead of disappearing.
 */
export function AudioPlayer({
  src,
  fallbackText,
  estimatedSeconds,
  available,
  label = "Listen",
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [failed, setFailed] = useState(false);
  const [rate, setRate] = useState(1);

  useEffect(() => {
    return () => {
      window.speechSynthesis?.cancel();
    };
  }, []);

  useEffect(() => {
    const audio = audioRef.current;
    if (audio) audio.playbackRate = rate;
  }, [rate]);

  const speakInBrowser = () => {
    const synth = window.speechSynthesis;
    if (!synth) return;

    if (synth.speaking) {
      synth.cancel();
      setPlaying(false);
      return;
    }

    const utterance = new SpeechSynthesisUtterance(fallbackText);
    utterance.rate = 0.95 * rate;
    utterance.pitch = 1;
    utterance.onend = () => setPlaying(false);
    utterance.onerror = () => setPlaying(false);
    synth.speak(utterance);
    setPlaying(true);
  };

  const toggle = async () => {
    if (!available || failed) {
      speakInBrowser();
      return;
    }

    const audio = audioRef.current;
    if (!audio) return;

    if (playing) {
      audio.pause();
      setPlaying(false);
      return;
    }

    try {
      setLoading(true);
      await audio.play();
      setPlaying(true);
    } catch {
      setFailed(true);
      speakInBrowser();
    } finally {
      setLoading(false);
    }
  };

  const duration = audioRef.current?.duration;
  const total = Number.isFinite(duration) && duration ? duration : estimatedSeconds ?? 0;

  const format = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="audio">
      <button
        className={`audio__button ${playing ? "audio__button--playing" : ""}`}
        onClick={() => void toggle()}
        aria-label={playing ? "Pause narration" : "Play narration"}
      >
        {loading ? "…" : playing ? "❚❚" : "▶"}
      </button>

      <div className="audio__body">
        <div className="audio__label">
          {label}
          {failed && <span className="audio__note"> · browser voice</span>}
          {!available && <span className="audio__note"> · browser voice</span>}
        </div>
        <div className="audio__track">
          <div className="audio__fill" style={{ width: `${progress * 100}%` }} />
        </div>
      </div>

      <div className="audio__meta">
        {total ? format(total * (1 - progress)) : "--:--"}
      </div>

      <select
        className="audio__rate"
        value={rate}
        onChange={(e) => setRate(Number(e.target.value))}
        aria-label="Playback speed"
      >
        <option value={0.75}>0.75×</option>
        <option value={1}>1×</option>
        <option value={1.25}>1.25×</option>
        <option value={1.5}>1.5×</option>
      </select>

      <audio
        ref={audioRef}
        src={src}
        preload="none"
        onTimeUpdate={(e) => {
          const el = e.currentTarget;
          if (el.duration) setProgress(el.currentTime / el.duration);
        }}
        onEnded={() => {
          setPlaying(false);
          setProgress(0);
        }}
        onError={() => setFailed(true)}
      />
    </div>
  );
}
