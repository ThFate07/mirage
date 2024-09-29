'use client';
import React, { useEffect, useRef, useState } from "react";
import { Upload, Play, FastForward } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface VideoData {
  codec: string;
  fileSize: number;
  bitrateData: { timestamp: number; bitrate: number }[];
}

export default function Home() {
  const [video, setVideo] = useState("");
  const [videoData, setVideoData] = useState<VideoData | null>(null);
  const [processedVideo, setProcessedVideo] = useState("");
  const [processedVideoData, setProcessedVideoData] = useState<VideoData | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const processedVideoRef = useRef<HTMLVideoElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const fileSizeInBytes = useRef(0);

  const processVideo = async (file: File) => {
    setIsProcessing(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://127.0.0.1:5328/api/upload", {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        const processedFileURL = `http://127.0.0.1:5328/api/processed/${data.processed_filename}`;
        setProcessedVideo(processedFileURL);
        setProcessedVideoData({
          codec: data.processed_info.codec,
          fileSize: data.processed_info.file_size,
          bitrateData: [],
        });
      } else {
        console.error("Error processing video:", response.statusText);
      }
    } catch (error) {
      console.error("Error uploading video:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  useEffect(() => {
    if (videoRef.current) {
      setVideoData({
        codec: "...",
        fileSize: fileSizeInBytes.current,
        bitrateData: [],
      });
    }
  }, [video]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-gray-100">
    <main className="container mx-auto p-8">
    <header className="mb-12 text-center">
    <h1 className="text-5xl font-extrabold mb-4 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-purple-500 to-pink-500">
    Mirage AI
    </h1>
    <p className="text-lg max-w-2xl mx-auto text-gray-300 font-light">
    Our AI technology identifies important video clips in CCTV footage and reduces the size of the tape by removing unwanted data, ensuring efficient surveillance video management.
    </p>
    </header>

    <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
    {/* Original Video */}
    <div className="bg-gray-800 rounded-xl overflow-hidden shadow-lg transition-all duration-300 hover:shadow-2xl">
    <div className="p-6">
    <h2 className="text-2xl font-semibold mb-4 flex items-center">
    <Play className="mr-2" size={24} />
    Original Video
    </h2>
    {video ? (
      <video className="w-full h-64 rounded-lg object-cover" controls src={video} ref={videoRef}></video>
    ) : (
      <div
      onClick={() => input.current && input.current.click()}
      className="border-2 border-dashed border-gray-600 h-64 flex items-center justify-center rounded-lg cursor-pointer hover:bg-gray-700 transition-colors duration-300"
      >
      <span className="text-sm text-gray-400 flex items-center">
      <Upload className="mr-2" size={20} />
      Click to select a video or drop it here
      </span>
      </div>
    )}
    </div>
    {videoData && (
      <div className="px-6 pb-6">
      <p className="text-sm text-gray-400">File size: {(videoData.fileSize / (1024 * 1024)).toFixed(2)} MB</p>
      <p className="text-sm text-gray-400">Codec: {videoData.codec}</p>
      </div>
    )}
    </div>

    {/* Processed Video */}
    <div className="bg-gray-800 rounded-xl overflow-hidden shadow-lg transition-all duration-300 hover:shadow-2xl">
    <div className="p-6">
    <h2 className="text-2xl font-semibold mb-4 flex items-center">
    <FastForward className="mr-2" size={24} />
    Processed Video
    </h2>
    {processedVideo ? (
      <video className="w-full h-64 rounded-lg object-cover" controls src={processedVideo} ref={processedVideoRef}></video>
    ) : (
      <div className="border-2 border-dashed border-gray-600 h-64 flex items-center justify-center rounded-lg">
      <span className="text-sm text-gray-400">No processed video available</span>
      </div>
    )}
    </div>
    {processedVideoData && (
      <div className="px-6 pb-6">
      <p className="text-sm text-gray-400">File size: {(processedVideoData.fileSize / (1024 * 1024)).toFixed(2)} MB</p>
      <p className="text-sm text-gray-400">Codec: {processedVideoData.codec}</p>
      </div>
    )}
    </div>
    </div>

    <div className="flex justify-center mb-8">
    <button
    onClick={() => input.current && input.current.click()}
    className="bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold py-3 px-8 rounded-lg shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-opacity-50 disabled:opacity-50"
    disabled={isProcessing}
    >
    {isProcessing ? 'Processing...' : 'Select a Video to Process'}
    </button>
    </div>

    {isProcessing && (
      <Alert>
      <AlertTitle>Processing Video</AlertTitle>
      <AlertDescription>
      Please wait while we analyze and optimize your video. This may take a few moments.
      </AlertDescription>
      </Alert>
    )}

    <input
    ref={input}
    onChange={(e) => {
      if (e.target.files) {
        const file = e.target.files[0];
        fileSizeInBytes.current = file.size;
        const url = URL.createObjectURL(file);
        setVideo(url);
        processVideo(file);
      }
    }}
    type="file"
    className="hidden"
    accept="video/*"
    />
    </main>
    </div>
  );
}
