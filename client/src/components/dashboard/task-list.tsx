import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { taskService, TaskSummary } from "@/services/task-service";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";

// Task card component
const TaskCard = ({ task }: { task: TaskSummary }) => {
  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
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
  
  // Extract task type from task ID
  const taskType = task.task_id.split('_')[0];
  
  // Get task type label
  const getTaskTypeLabel = (type: string) => {
    switch (type) {
      case 'video':
        return 'Video Generation';
      case 'script':
        return 'Script Generation';
      case 'edit':
        return 'Component Edit';
      default:
        return 'Task';
    }
  };
  
  return (
    <div className="bg-white/5 border border-white/10 rounded-lg p-4">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <div className="bg-primary/10 p-2 rounded-full text-primary">
            {taskType === 'video' && (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="m22 8-6-6H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"></path>
                <path d="M18 8h-6V2"></path>
              </svg>
            )}
            {taskType === 'script' && (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <line x1="10" y1="9" x2="8" y2="9"></line>
              </svg>
            )}
            {taskType === 'edit' && (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 20h9"></path>
                <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
              </svg>
            )}
          </div>
          <h3 className="text-sm font-medium">{getTaskTypeLabel(taskType)}</h3>
        </div>
        <div className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(task.status)}`}>
          {task.status.charAt(0).toUpperCase() + task.status.slice(1)}
        </div>
      </div>
      
      <div className="mb-3">
        <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
          <div 
            className={`h-full rounded-full transition-all duration-500 ease-out ${
              task.status === 'completed' 
                ? 'bg-green-500/80' 
                : task.status === 'failed'
                  ? 'bg-red-500/80'
                  : 'bg-primary/80'
            }`}
            style={{ width: `${task.progress}%` }}
          ></div>
        </div>
        <div className="mt-1 text-xs text-muted-foreground flex justify-between">
          <span>Progress: {task.progress}%</span>
          <span>ID: {task.task_id}</span>
        </div>
      </div>
      
      <div className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground">
          {formatDate(task.created_at)}
        </div>
        
        <Button 
          asChild
          size="sm" 
          variant={task.status === 'completed' ? 'default' : 'outline'}
        >
          <Link to={taskService.resumeTask(task)}>
            {task.status === 'completed' ? 'View Result' : 'Resume'}
          </Link>
        </Button>
      </div>
    </div>
  );
};

export default function TaskList() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [filteredTasks, setFilteredTasks] = useState<TaskSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filter state
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  
  useEffect(() => {
    const fetchTasks = async () => {
      try {
        setLoading(true);
        
        // Fetch tasks
        const tasksData = await taskService.getUserTasks();
        setTasks(tasksData);
        setFilteredTasks(tasksData);
      } catch (err) {
        console.error("Error fetching tasks:", err);
        setError("Failed to load tasks");
      } finally {
        setLoading(false);
      }
    };
    
    fetchTasks();
  }, []);
  
  useEffect(() => {
    // Apply filters
    let result = [...tasks];
    
    // Apply status filter
    if (statusFilter !== "all") {
      result = result.filter(task => task.status === statusFilter);
    }
    
    // Apply type filter
    if (typeFilter !== "all") {
      result = result.filter(task => task.task_id.startsWith(typeFilter));
    }
    
    // Sort by creation time (newest first)
    result.sort((a, b) => b.created_at - a.created_at);
    
    setFilteredTasks(result);
  }, [tasks, statusFilter, typeFilter]);
  
  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="h-8 w-8 rounded-full border-4 border-primary border-t-transparent animate-spin"></div>
      </div>
    );
  }
  
  return (
    <div className="bg-white/5 border border-white/10 rounded-lg p-4 mb-8">
      <div className="flex flex-col md:flex-row items-center justify-between mb-4 gap-4">
        <h2 className="text-lg font-medium">Recent Tasks</h2>
        
        <div className="flex flex-col md:flex-row gap-4 w-full md:w-auto">
          <div className="w-full md:w-auto">
            <Label htmlFor="status-filter" className="sr-only">Status</Label>
            <Select 
              value={statusFilter} 
              onValueChange={setStatusFilter}
            >
              <SelectTrigger id="status-filter" className="w-full md:w-[150px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="processing">Processing</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div className="w-full md:w-auto">
            <Label htmlFor="type-filter" className="sr-only">Type</Label>
            <Select 
              value={typeFilter} 
              onValueChange={setTypeFilter}
            >
              <SelectTrigger id="type-filter" className="w-full md:w-[150px]">
                <SelectValue placeholder="Filter by type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="video">Video Generation</SelectItem>
                <SelectItem value="script">Script Generation</SelectItem>
                <SelectItem value="edit">Component Edits</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
      
      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
          <p className="text-red-500">{error}</p>
        </div>
      )}
      
      {filteredTasks.length === 0 ? (
        <div className="bg-white/5 border border-white/10 rounded-lg p-8 text-center">
          <h3 className="text-lg font-medium mb-2">No tasks found</h3>
          <p className="text-muted-foreground mb-4">
            {tasks.length === 0 
              ? "You haven't created any tasks yet." 
              : "No tasks match your current filters."}
          </p>
          
          {tasks.length === 0 && (
            <Button asChild>
              <Link to="/generation">Create Your First Video</Link>
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTasks.map(task => (
            <TaskCard key={task.task_id} task={task} />
          ))}
        </div>
      )}
    </div>
  );
}
