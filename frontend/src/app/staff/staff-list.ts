import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { Api, errorMessage } from '../core/api';
import { City, ROLES, Role, StaffMember } from '../core/models';
import { RoleLabelPipe } from '../core/role-label-pipe';

@Component({
  selector: 'app-staff-list',
  imports: [FormsModule, RoleLabelPipe],
  templateUrl: './staff-list.html',
})
export class StaffList implements OnInit {
  private readonly api = inject(Api);

  protected readonly roles = ROLES;
  protected readonly cities = signal<City[]>([]);
  protected readonly staff = signal<StaffMember[]>([]);
  protected readonly error = signal<string | null>(null);

  protected role: Role | '' = '';
  protected city: number | null = null;

  ngOnInit(): void {
    this.api.cities().subscribe((cities) => this.cities.set(cities));
    this.load();
  }

  protected load(): void {
    this.api.staff({ role: this.role, city: this.city }).subscribe({
      next: (staff) => this.staff.set(staff),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }
}
