export default function Home() {
  return (
    <div className="antialiased bg-gray-50 dark:bg-gray-900">
      <main className="p-4 h-auto pt-20">
        <div className="border-2 border-dashed rounded-lg border-gray-300 dark:border-gray-600 h-96 mb-4">Heading</div>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="border-2 border-dashed rounded-lg border-gray-300 dark:border-gray-600 h-48 md:h-72">
            Before Process Image
          </div>
          <div className="border-2 border-dashed rounded-lg border-gray-300 dark:border-gray-600 h-48 md:h-72">
            After Process Image
          </div>
          <div className="border-2 border-dashed rounded-lg border-gray-300 dark:border-gray-600 h-48 md:h-72">
            Before Process Image Statistics
          </div>
          <div className="border-2 border-dashed rounded-lg border-gray-300 dark:border-gray-600 h-48 md:h-72">
            After Process Image Statistics
          </div>
        </div>
      </main>
    </div>
  );
}
