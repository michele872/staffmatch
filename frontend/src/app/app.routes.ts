import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'shifts' },
  {
    path: 'shifts',
    title: 'Shifts · StaffMatch',
    loadComponent: () => import('./shifts/shift-list').then((m) => m.ShiftList),
  },
  {
    path: 'shifts/new',
    title: 'New shift · StaffMatch',
    loadComponent: () => import('./shifts/shift-form').then((m) => m.ShiftForm),
  },
  {
    path: 'shifts/:id',
    title: 'Shift · StaffMatch',
    loadComponent: () => import('./shifts/shift-detail').then((m) => m.ShiftDetail),
  },
  {
    path: 'staff',
    title: 'Staff · StaffMatch',
    loadComponent: () => import('./staff/staff-list').then((m) => m.StaffList),
  },
  { path: '**', redirectTo: 'shifts' },
];
