"use client";

import { useRef, useState } from "react";

export default function Home() {
  const [video, setVideo] = useState("");
  const [processedVideo, setProcessedVideo] = useState("");
  const [resolution, setResolution] = useState({ width: 0, height: 0 });
  const [duration, setDuration] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const fileSizeInBytes = useRef(0);

  const processVideo = async (url: string) => {
    await new Promise((resolve) => setTimeout(resolve, 5000));
    setProcessedVideo(url);
  };

  const handleMetadataLoaded = () => {
    if (videoRef.current) {
      const width = videoRef.current.videoWidth;
      const height = videoRef.current.videoHeight;
      setResolution({ width, height }); // Set resolution in state

      const duration = videoRef.current.duration;
      setDuration(duration);
    }
  };

  return (
    <div className="antialiased bg-gray-50 dark:bg-gray-900">
      <main className="p-4 h-auto pt-20">
        <div className=" rounded-lg border-gray-300 dark:border-gray-600 h-60 mb-4">
          <h1 className="mb-4 text-3xl font-extrabold text-gray-900 dark:text-white md:text-5xl lg:text-6xl">
            <span className="text-transparent bg-clip-text bg-gradient-to-r to-emerald-600 from-sky-400">Mirage</span>{" "}
            AI.
          </h1>
          <p className="text-lg font-normal text-gray-500 lg:text-xl dark:text-gray-400">
            Our AI technology identifies important video clips in CCTV footage and reduces the size of the tape by
            removing unwanted data. This ensures that only the most relevant information is retained, making it easier
            to review and store surveillance videos efficiently.
          </p>
        </div>
        <div className="flex">
          <div className="w-1/2 flex justify-between p-2">
            <h1>Before Processing</h1>
            {video && (
              <button
                onClick={() => {
                  input.current && input.current.click();
                }}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke-width="1.5"
                  stroke="currentColor"
                  className="text-green-500 dark:text-green-400 h-5 w-5"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z"
                  />
                </svg>
              </button>
            )}
          </div>
          <div className="w-1/2 flex justify-between p-2">
            <h1>After Processing</h1>
            {processedVideo && (
              <a href={processedVideo} download="processed_video.mp4">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke-width="1.5"
                  stroke="currentColor"
                  className="text-green-500 dark:text-green-400 h-5 w-5"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
                  />
                </svg>
              </a>
            )}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className=" border-gray-300 dark:border-gray-600 h-96">
            {video ? (
              <video
                className="w-full h-full"
                controls
                src={video}
                ref={videoRef}
                onLoadedMetadata={handleMetadataLoaded}
              ></video>
            ) : (
              <div className="border-2 border-dashed rounded-lg border-gray-300 dark:border-gray-600 h-full flex justify-center">
                <button
                  onClick={() => input.current && input.current.click()}
                  type="button"
                  className="text-white bg-gradient-to-br from-green-400 to-blue-600 hover:bg-gradient-to-bl focus:ring-4 focus:outline-none focus:ring-green-200 dark:focus:ring-green-800 font-medium rounded-lg text-sm px-5 py-2.5 text-center me-2 my-auto h-10"
                >
                  Select a video
                </button>
              </div>
            )}
          </div>
          <input
            ref={input}
            onChange={(e) => {
              if (e.target.files) {
                const file = e.target.files[0];
                fileSizeInBytes.current = file.size;

                const url = URL.createObjectURL(file);
                setVideo(url);
                processVideo(url);
              }
            }}
            className="hidden"
            id="file_input"
            type="file"
            accept="video/*"
          />
          <div className="h-96">
            {video ? (
              processedVideo ? (
                <video className="w-full h-full" controls src={processedVideo}></video>
              ) : (
                <div className="border-2 border-dashed rounded-lg border-gray-300 dark:border-gray-600 h-full flex justify-center">
                  <h3 className=" my-auto text-slate-100">Proccessing...</h3>
                </div>
              )
            ) : (
              <div className="border-2 border-dashed rounded-lg border-gray-300 dark:border-gray-600 h-full flex justify-center">
                <h3 className=" my-auto text-slate-100">No video to process</h3>
              </div>
            )}
          </div>
          <div className="border-2 border-dashed rounded-lg border-gray-300 dark:border-gray-600 h-48 md:h-72">
            Before Process Image Statistics
            {video ? (
              <div>
                <p>Codec: </p>
                <p>File Size: {(fileSizeInBytes.current / 1024 / 1024).toFixed(3)} MB</p>
                <p>
                  Resolution: {resolution.height} x {resolution.width}
                </p>
                <p>
                  Duration: {duration > 60 ? (duration / 60).toString() + " Minute" : duration.toString() + " Seconds"}{" "}
                </p>
                <p>Bitrate: </p>
              </div>
            ) : (
              ""
            )}
          </div>
          <div className="border-2 border-dashed rounded-lg border-gray-300 dark:border-gray-600 h-48 md:h-72">
            After Process Image Statistics
          </div>
        </div>
      </main>
    </div>
  );
}
