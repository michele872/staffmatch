import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Api, errorMessage } from '../core/api';
import { ShiftSummary } from '../core/models';

@Component({
  selector: 'app-shift-list',
  imports: [RouterLink, DatePipe],
  templateUrl: './shift-list.html',
})
export class ShiftList implements OnInit {
  private readonly api = inject(Api);

  protected readonly shifts = signal<ShiftSummary[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.api.shifts().subscribe({
      next: (shifts) => {
        this.shifts.set(shifts);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(errorMessage(err));
        this.loading.set(false);
      },
    });
  }

  protected progress(shift: ShiftSummary): number {
    return shift.required_staff ? Math.round((shift.assigned_staff / shift.required_staff) * 100) : 0;
  }
}
