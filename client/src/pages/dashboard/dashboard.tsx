import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { videoService, Video } from "@/services/video-service";
import { userService } from "@/services/user-service";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

// Stats card component
const StatsCard = ({ title, value, icon }: { title: string; value: string | number; icon: React.ReactNode }) => (
  <div className="bg-background/5 border border-border/20 rounded-lg p-4 flex items-center gap-4">
    <div className="bg-primary/10 p-3 rounded-full text-primary">
      {icon}
    </div>
    <div>
      <p className="text-sm text-muted-foreground">{title}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  </div>
);

// Video card component
const VideoCard = ({ video, onDelete }: { video: Video; onDelete: (id: string) => void }) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }).format(date);
  };
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-500 bg-green-500/10';
      case 'processing':
        return 'text-blue-500 bg-blue-500/10';
      case 'failed':
        return 'text-red-500 bg-red-500/10';
      default:
        return 'text-gray-500 bg-gray-500/10';
    }
  };
  
  return (
    <div className="bg-background/5 border border-border/20 rounded-lg p-4 flex flex-col md:flex-row gap-4">
      <div className="w-full md:w-1/4 aspect-video bg-black/20 rounded-md overflow-hidden">
        {video.thumbnail_url ? (
          <img 
            src={video.thumbnail_url} 
            alt={video.title} 
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-muted-foreground">
            No thumbnail
          </div>
        )}
      </div>
      
      <div className="w-full md:w-3/4 flex flex-col">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
          <h3 className="text-lg font-medium">{video.title}</h3>
          <div className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(video.status)}`}>
            {video.status.charAt(0).toUpperCase() + video.status.slice(1)}
          </div>
        </div>
        
        <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{video.prompt}</p>
        
        <div className="text-xs text-muted-foreground mt-2">
          Created: {formatDate(video.created_at)}
        </div>
        
        <div className="mt-4 flex flex-wrap gap-2">
          {video.status === 'completed' && (
            <>
              <Button asChild size="sm" variant="default">
                <Link to={`/editor?video=${video.id}`}>Edit</Link>
              </Button>
              
              {video.output_url && (
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={() => window.open(video.output_url, '_blank')}
                >
                  View
                </Button>
              )}
            </>
          )}
          
          {video.status === 'processing' && (
            <Button size="sm" variant="outline">
              Cancel
            </Button>
          )}
          
          {video.status === 'failed' && (
            <Button size="sm" variant="outline">
              Retry
            </Button>
          )}
          
          <Button 
            size="sm" 
            variant="destructive" 
            onClick={() => onDelete(video.id)}
          >
            Delete
          </Button>
        </div>
      </div>
    </div>
  );
};

export default function Dashboard() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [filteredVideos, setFilteredVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [credits, setCredits] = useState(0);
  
  // Filter state
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortOrder, setSortOrder] = useState("newest");
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Fetch videos
        const videosData = await videoService.getVideos();
        setVideos(videosData);
        setFilteredVideos(videosData);
        
        // Fetch user credits
        const userCredits = await userService.getCredits();
        setCredits(userCredits);
      } catch (err) {
        console.error("Error fetching dashboard data:", err);
        setError("Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);
  
  useEffect(() => {
    // Apply filters and sorting
    let result = [...videos];
    
    // Apply status filter
    if (statusFilter !== "all") {
      result = result.filter(video => video.status === statusFilter);
    }
    
    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(
        video => 
          video.title.toLowerCase().includes(term) || 
          video.prompt.toLowerCase().includes(term)
      );
    }
    
    // Apply sorting
    result.sort((a, b) => {
      const dateA = new Date(a.created_at).getTime();
      const dateB = new Date(b.created_at).getTime();
      
      if (sortOrder === "newest") {
        return dateB - dateA;
      } else {
        return dateA - dateB;
      }
    });
    
    setFilteredVideos(result);
  }, [videos, statusFilter, searchTerm, sortOrder]);
  
  const handleDeleteVideo = async (id: string) => {
    if (window.confirm("Are you sure you want to delete this video?")) {
      try {
        await videoService.deleteVideo(id);
        setVideos(videos.filter(video => video.id !== id));
      } catch (err) {
        console.error("Error deleting video:", err);
        alert("Failed to delete video");
      }
    }
  };
  
  // Calculate stats
  const totalVideos = videos.length;
  const completedVideos = videos.filter(v => v.status === 'completed').length;
  const successRate = totalVideos > 0 
    ? Math.round((completedVideos / totalVideos) * 100) 
    : 0;
  
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-12 w-12 rounded-full border-4 border-primary border-t-transparent animate-spin"></div>
      </div>
    );
  }
  
  return (
    <div className="container max-w-6xl mx-auto py-8 px-4">
      <div className="flex flex-col md:flex-row items-center justify-between mb-8 gap-4">
        <h1 className="text-3xl font-bold">My Dashboard</h1>
        
        <Button asChild>
          <Link to="/generation">Create New Video</Link>
        </Button>
      </div>
      
      {error && (
        <div className="mb-8 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
          <p className="text-red-500">{error}</p>
        </div>
      )}
      
      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <StatsCard 
          title="Total Videos" 
          value={totalVideos} 
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m22 8-6-6H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"></path>
              <path d="M18 8h-6V2"></path>
            </svg>
          } 
        />
        
        <StatsCard 
          title="Available Credits" 
          value={credits} 
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M12 6v12"></path>
              <path d="M8 12h8"></path>
            </svg>
          } 
        />
        
        <StatsCard 
          title="Success Rate" 
          value={`${successRate}%`} 
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
              <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
          } 
        />
      </div>
      
      {/* Filters */}
      <div className="bg-background/5 border border-border/20 rounded-lg p-4 mb-8">
        <h2 className="text-lg font-medium mb-4">My Videos</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <Label htmlFor="search" className="mb-2 block">Search</Label>
            <Input 
              id="search" 
              placeholder="Search by title or prompt" 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          
          <div>
            <Label htmlFor="status" className="mb-2 block">Status</Label>
            <Select 
              value={statusFilter} 
              onValueChange={setStatusFilter}
            >
              <SelectTrigger id="status">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="processing">Processing</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div>
            <Label htmlFor="sort" className="mb-2 block">Sort</Label>
            <Select 
              value={sortOrder} 
              onValueChange={setSortOrder}
            >
              <SelectTrigger id="sort">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="newest">Newest first</SelectItem>
                <SelectItem value="oldest">Oldest first</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
      
      {/* Video list */}
      <div className="space-y-4">
        {filteredVideos.length === 0 ? (
          <div className="bg-background/5 border border-border/20 rounded-lg p-8 text-center">
            <h3 className="text-lg font-medium mb-2">No videos found</h3>
            <p className="text-muted-foreground mb-4">
              {videos.length === 0 
                ? "You haven't created any videos yet." 
                : "No videos match your current filters."}
            </p>
            
            {videos.length === 0 && (
              <Button asChild>
                <Link to="/generation">Create Your First Video</Link>
              </Button>
            )}
          </div>
        ) : (
          filteredVideos.map(video => (
            <VideoCard 
              key={video.id} 
              video={video} 
              onDelete={handleDeleteVideo} 
            />
          ))
        )}
      </div>
    </div>
  );
}
