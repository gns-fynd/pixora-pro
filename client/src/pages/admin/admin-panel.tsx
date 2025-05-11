import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/api-client';
import useAuthStore from '@/store/use-auth-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { IconTrash, IconPlus, IconRefresh, IconCreditCard } from '@tabler/icons-react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

// Types
interface User {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  credits: number;
  created_at: string;
}

interface Voice {
  id: string;
  name: string;
  gender: string;
  tone: string;
  preview_url: string;
  is_default: boolean;
}

export default function AdminPanel() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const [users, setUsers] = useState<User[]>([]);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Credit adjustment state
  const [creditDialogOpen, setCreditDialogOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [creditAmount, setCreditAmount] = useState(0);
  const [creditReason, setCreditReason] = useState('');
  
  // Voice creation state
  const [voiceDialogOpen, setVoiceDialogOpen] = useState(false);
  const [voiceName, setVoiceName] = useState('');
  const [voiceGender, setVoiceGender] = useState('male');
  const [voiceTone, setVoiceTone] = useState('professional');
  const [voiceAudioUrl, setVoiceAudioUrl] = useState('');
  const [isDefaultVoice, setIsDefaultVoice] = useState(false);
  
  // Check if user is admin
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/auth');
      return;
    }
    
    // Fetch users to check if admin
    fetchUsers();
  }, [isAuthenticated, navigate]);
  
  // Fetch users
  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.get<User[]>('/admin/users');
      setUsers(response);
      
      // Also fetch voices
      fetchVoices();
    } catch (err) {
      console.error('Error fetching users:', err);
      setError('You do not have permission to access the admin panel.');
      setLoading(false);
    }
  };
  
  // Fetch voices
  const fetchVoices = async () => {
    try {
      const response = await apiClient.get<Voice[]>('/admin/voices');
      setVoices(response);
    } catch (err) {
      console.error('Error fetching voices:', err);
    } finally {
      setLoading(false);
    }
  };
  
  // Handle credit adjustment
  const handleCreditAdjustment = async () => {
    if (!selectedUserId || !creditReason) return;
    
    try {
      await apiClient.post('/admin/credits', {
        user_id: selectedUserId,
        amount: creditAmount,
        reason: creditReason
      });
      
      // Refresh users
      fetchUsers();
      
      // Reset form
      setCreditDialogOpen(false);
      setSelectedUserId(null);
      setCreditAmount(0);
      setCreditReason('');
    } catch (err) {
      console.error('Error adjusting credits:', err);
      setError('Failed to adjust credits.');
    }
  };
  
  // Handle voice creation
  const handleVoiceCreation = async () => {
    if (!voiceName || !voiceAudioUrl) return;
    
    try {
      await apiClient.post('/admin/voices', {
        name: voiceName,
        gender: voiceGender,
        tone: voiceTone,
        audio_url: voiceAudioUrl,
        is_default: isDefaultVoice
      });
      
      // Refresh voices
      fetchVoices();
      
      // Reset form
      setVoiceDialogOpen(false);
      setVoiceName('');
      setVoiceGender('male');
      setVoiceTone('professional');
      setVoiceAudioUrl('');
      setIsDefaultVoice(false);
    } catch (err) {
      console.error('Error creating voice:', err);
      setError('Failed to create voice.');
    }
  };
  
  // Handle voice deletion
  const handleVoiceDeletion = async (voiceId: string) => {
    if (!confirm('Are you sure you want to delete this voice?')) return;
    
    try {
      await apiClient.delete(`/admin/voices/${voiceId}`);
      
      // Refresh voices
      fetchVoices();
    } catch (err) {
      console.error('Error deleting voice:', err);
      setError('Failed to delete voice.');
    }
  };
  
  // Format date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };
  
  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-screen">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardHeader>
            <CardTitle>Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{error}</p>
          </CardContent>
          <CardFooter>
            <Button onClick={() => navigate('/')}>Go Home</Button>
          </CardFooter>
        </Card>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Admin Panel</h1>
      
      <Tabs defaultValue="users">
        <TabsList className="mb-6">
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="voices">Voice Models</TabsTrigger>
        </TabsList>
        
        {/* Users Tab */}
        <TabsContent value="users">
          <Card>
            <CardHeader>
              <CardTitle>User Management</CardTitle>
              <CardDescription>Manage users and credits</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Email</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Credits</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map(user => (
                      <TableRow key={user.id}>
                        <TableCell>{user.email}</TableCell>
                        <TableCell>{user.name || '-'}</TableCell>
                        <TableCell>{user.credits}</TableCell>
                        <TableCell>{formatDate(user.created_at)}</TableCell>
                        <TableCell>
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => {
                              setSelectedUserId(user.id);
                              setCreditDialogOpen(true);
                            }}
                          >
                            <IconCreditCard size={16} className="mr-2" />
                            Adjust Credits
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
            <CardFooter>
              <Button onClick={fetchUsers}>
                <IconRefresh size={16} className="mr-2" />
                Refresh
              </Button>
            </CardFooter>
          </Card>
          
          {/* Credit Adjustment Dialog */}
          <Dialog open={creditDialogOpen} onOpenChange={setCreditDialogOpen}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Adjust Credits</DialogTitle>
                <DialogDescription>
                  Add or remove credits from a user's account.
                </DialogDescription>
              </DialogHeader>
              
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="creditAmount" className="text-right">
                    Amount
                  </Label>
                  <Input
                    id="creditAmount"
                    type="number"
                    value={creditAmount}
                    onChange={(e) => setCreditAmount(parseInt(e.target.value))}
                    className="col-span-3"
                    placeholder="Enter positive number to add, negative to deduct"
                  />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="creditReason" className="text-right">
                    Reason
                  </Label>
                  <Input
                    id="creditReason"
                    value={creditReason}
                    onChange={(e) => setCreditReason(e.target.value)}
                    className="col-span-3"
                    placeholder="Reason for adjustment"
                  />
                </div>
              </div>
              
              <DialogFooter>
                <Button variant="outline" onClick={() => setCreditDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleCreditAdjustment}>
                  Adjust Credits
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </TabsContent>
        
        {/* Voices Tab */}
        <TabsContent value="voices">
          <Card>
            <CardHeader>
              <CardTitle>Voice Models</CardTitle>
              <CardDescription>Manage voice models for narration</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-4">
                <Button onClick={() => setVoiceDialogOpen(true)}>
                  <IconPlus size={16} className="mr-2" />
                  Add Voice
                </Button>
              </div>
              
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Gender</TableHead>
                      <TableHead>Tone</TableHead>
                      <TableHead>Default</TableHead>
                      <TableHead>Preview</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {voices.map(voice => (
                      <TableRow key={voice.id}>
                        <TableCell>{voice.name}</TableCell>
                        <TableCell className="capitalize">{voice.gender}</TableCell>
                        <TableCell className="capitalize">{voice.tone}</TableCell>
                        <TableCell>{voice.is_default ? 'Yes' : 'No'}</TableCell>
                        <TableCell>
                          <audio controls src={voice.preview_url} className="h-8"></audio>
                        </TableCell>
                        <TableCell>
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => handleVoiceDeletion(voice.id)}
                          >
                            <IconTrash size={16} className="mr-2" />
                            Delete
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
            <CardFooter>
              <Button onClick={fetchVoices}>
                <IconRefresh size={16} className="mr-2" />
                Refresh
              </Button>
            </CardFooter>
          </Card>
          
          {/* Voice Creation Dialog */}
          <Dialog open={voiceDialogOpen} onOpenChange={setVoiceDialogOpen}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Voice Model</DialogTitle>
                <DialogDescription>
                  Create a new voice model for narration.
                </DialogDescription>
              </DialogHeader>
              
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="voiceName" className="text-right">
                    Name
                  </Label>
                  <Input
                    id="voiceName"
                    value={voiceName}
                    onChange={(e) => setVoiceName(e.target.value)}
                    className="col-span-3"
                    placeholder="Professional Male"
                  />
                </div>
                
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="voiceGender" className="text-right">
                    Gender
                  </Label>
                  <Select
                    value={voiceGender}
                    onValueChange={setVoiceGender}
                  >
                    <SelectTrigger className="col-span-3">
                      <SelectValue placeholder="Select gender" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="male">Male</SelectItem>
                      <SelectItem value="female">Female</SelectItem>
                      <SelectItem value="neutral">Neutral</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="voiceTone" className="text-right">
                    Tone
                  </Label>
                  <Select
                    value={voiceTone}
                    onValueChange={setVoiceTone}
                  >
                    <SelectTrigger className="col-span-3">
                      <SelectValue placeholder="Select tone" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="professional">Professional</SelectItem>
                      <SelectItem value="casual">Casual</SelectItem>
                      <SelectItem value="energetic">Energetic</SelectItem>
                      <SelectItem value="calm">Calm</SelectItem>
                      <SelectItem value="serious">Serious</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="voiceAudioUrl" className="text-right">
                    Audio URL
                  </Label>
                  <Input
                    id="voiceAudioUrl"
                    value={voiceAudioUrl}
                    onChange={(e) => setVoiceAudioUrl(e.target.value)}
                    className="col-span-3"
                    placeholder="https://example.com/audio.mp3"
                  />
                </div>
                
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="isDefaultVoice" className="text-right">
                    Default
                  </Label>
                  <div className="flex items-center space-x-2 col-span-3">
                    <input
                      type="checkbox"
                      id="isDefaultVoice"
                      checked={isDefaultVoice}
                      onChange={(e) => setIsDefaultVoice(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                    <Label htmlFor="isDefaultVoice">
                      Set as default voice
                    </Label>
                  </div>
                </div>
              </div>
              
              <DialogFooter>
                <Button variant="outline" onClick={() => setVoiceDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleVoiceCreation}>
                  Create Voice
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </TabsContent>
      </Tabs>
    </div>
  );
}
