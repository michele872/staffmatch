import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import {
  City,
  ShiftDetail,
  ShiftDraft,
  ShiftSummary,
  Meta,
  NewShift,
  Role,
  RolePlan,
  StaffMember,
} from './models';

/** Thin typed wrapper around the Django REST API (served under /api). */
@Injectable({ providedIn: 'root' })
export class Api {
  private readonly http = inject(HttpClient);
  private readonly base = '/api';

  meta(): Observable<Meta> {
    return this.http.get<Meta>(`${this.base}/meta/`);
  }

  cities(): Observable<City[]> {
    return this.http.get<City[]>(`${this.base}/cities/`);
  }

  staff(filters: { role?: Role | ''; city?: number | null } = {}): Observable<StaffMember[]> {
    let params = new HttpParams();
    if (filters.role) params = params.set('role', filters.role);
    if (filters.city) params = params.set('city', filters.city);
    return this.http.get<StaffMember[]>(`${this.base}/staff/`, { params });
  }

  shifts(): Observable<ShiftSummary[]> {
    return this.http.get<ShiftSummary[]>(`${this.base}/shifts/`);
  }

  shift(id: number): Observable<ShiftDetail> {
    return this.http.get<ShiftDetail>(`${this.base}/shifts/${id}/`);
  }

  createShift(shift: NewShift): Observable<ShiftDetail> {
    return this.http.post<ShiftDetail>(`${this.base}/shifts/`, shift);
  }

  deleteShift(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/shifts/${id}/`);
  }

  plan(id: number): Observable<RolePlan[]> {
    return this.http.get<RolePlan[]>(`${this.base}/shifts/${id}/plan/`);
  }

  assign(id: number): Observable<ShiftDetail> {
    return this.http.post<ShiftDetail>(`${this.base}/shifts/${id}/assign/`, {});
  }

  removeAssignment(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/assignments/${id}/`);
  }

  draftFromText(text: string): Observable<ShiftDraft> {
    return this.http.post<ShiftDraft>(`${this.base}/shifts/draft-from-text/`, { text });
  }
}

/** Turns an API error into a message that can be shown to the user. */
export function errorMessage(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    if (typeof error.error?.detail === 'string') return error.error.detail;
    if (error.status === 0) return 'The server cannot be reached.';
    if (error.error && typeof error.error === 'object') {
      return Object.entries(error.error)
        .map(([field, messages]) => `${field}: ${[messages].flat(3).join(' ')}`)
        .join(' · ');
    }
  }
  return 'Something went wrong, please try again.';
}
