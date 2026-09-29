export type Role = 'NURSE' | 'CARE_ASSISTANT' | 'PHYSIOTHERAPIST' | 'DOCTOR';

export const ROLES: readonly Role[] = ['NURSE', 'CARE_ASSISTANT', 'PHYSIOTHERAPIST', 'DOCTOR'];

export const ROLE_LABELS: Record<Role, string> = {
  NURSE: 'Nurse',
  CARE_ASSISTANT: 'Care assistant',
  PHYSIOTHERAPIST: 'Physiotherapist',
  DOCTOR: 'Doctor',
};

export interface City {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
}

export interface StaffMember {
  id: number;
  full_name: string;
  role: Role;
  city: number;
  city_name: string;
  max_travel_km: number;
  active: boolean;
}

export interface RoleRequirement {
  role: Role;
  quantity: number;
}

export interface Assignment {
  id: number;
  staff: number;
  staff_name: string;
  staff_city: string;
  role: Role;
  distance_km: string;
}

export interface ShiftSummary {
  id: number;
  title: string;
  date: string;
  city: number;
  city_name: string;
  patients: number;
  required_staff: number;
  assigned_staff: number;
}

export interface ShiftDetail {
  id: number;
  title: string;
  date: string;
  city: number;
  city_name: string;
  patients: number;
  notes: string;
  requirements: RoleRequirement[];
  assignments: Assignment[];
  created_at: string;
}

export interface NewShift {
  title: string;
  date: string;
  city: number;
  patients: number;
  notes: string;
  requirements: RoleRequirement[];
}

export interface Candidate {
  staff: number;
  staff_name: string;
  staff_city: string;
  distance_km: string;
}

export interface RolePlan {
  role: Role;
  required: number;
  already_assigned: number;
  missing: number;
  candidates: Candidate[];
}

/** Draft produced by the AI intake. Every field may be missing. */
export interface ShiftDraft {
  title: string;
  date: string | null;
  city: number | null;
  patients: number | null;
  notes: string;
  requirements: RoleRequirement[];
}

export interface Meta {
  ai_intake_enabled: boolean;
}
