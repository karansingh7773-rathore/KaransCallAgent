export enum UserRole {
  NONE = 'NONE',
  HOMEOWNER = 'HOMEOWNER',
  POLICE = 'POLICE'
}

export interface CameraNode {
  id: string;
  ownerName: string;
  address: string;
  lat: number;
  lng: number;
  contact: string;
  hasFootage: boolean;
  registeredDate: string;
  isPrivate: boolean; // Privacy mode toggle
}

export enum RequestStatus {
  PENDING = 'PENDING',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED'
}

export interface AccessRequest {
  id: string;
  cameraId: string;
  requestDate: string;
  incidentTime: string;
  reason: string;
  status: RequestStatus;
  videoUrl?: string; // Blob URL for preview
  videoFile?: File; // Actual file for AI
}

export interface ChatMessage {
  role: 'user' | 'model';
  text: string;
  timestamp: Date;
}

export interface Incident {
  id: string;
  type: string;
  description: string;
  lat: number;
  lng: number;
  timestamp: string;
  radius: number; // Search radius in meters
}

export interface CommunityAlert {
  id: string;
  title: string;
  message: string;
  severity: 'high' | 'medium' | 'low';
  date: string;
}

// Mock Data Types - Centered roughly around San Francisco for demo
export const MOCK_CAMERAS: CameraNode[] = [
  { id: 'c1', ownerName: 'John Doe', address: '123 Market St', lat: 37.7749, lng: -122.4194, contact: '555-0101', hasFootage: true, registeredDate: '2023-11-15', isPrivate: false },
  { id: 'c2', ownerName: 'Jane Smith', address: '456 Mission St', lat: 37.7849, lng: -122.4094, contact: '555-0102', hasFootage: true, registeredDate: '2024-01-20', isPrivate: false },
  { id: 'c3', ownerName: 'Robert Johnson', address: '789 Van Ness', lat: 37.7949, lng: -122.4294, contact: '555-0103', hasFootage: true, registeredDate: '2024-02-10', isPrivate: false },
  { id: 'c4', ownerName: 'Emily Davis', address: '321 Castro St', lat: 37.7609, lng: -122.4350, contact: '555-0104', hasFootage: true, registeredDate: '2023-12-05', isPrivate: false },
  { id: 'c5', ownerName: 'Michael Chen', address: '555 Haight St', lat: 37.7719, lng: -122.4450, contact: '555-0105', hasFootage: true, registeredDate: '2024-03-01', isPrivate: true }, // Private by default
];

export const MOCK_INCIDENTS: Incident[] = [
  { id: 'i1', type: 'Theft', description: 'Vehicle break-in reported', lat: 37.7755, lng: -122.4180, timestamp: '10 mins ago', radius: 300 },
  { id: 'i2', type: 'Assault', description: 'Physical altercation in public park', lat: 37.7615, lng: -122.4340, timestamp: '1 hour ago', radius: 500 },
];

export const MOCK_ALERTS: CommunityAlert[] = [
  { id: 'a1', title: 'Suspicious Vehicle', message: 'Blue Sedan with plate ending 456 seen circling blocks near Market St.', severity: 'medium', date: 'Today, 10:30 AM' },
  { id: 'a2', title: 'Package Thief', message: 'Person in red hoodie reported stealing packages in Mission District.', severity: 'low', date: 'Yesterday' },
];

declare global {
  namespace JSX {
    interface IntrinsicElements {
      'iconify-icon': any;
    }
  }
}
