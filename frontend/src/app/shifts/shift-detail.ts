import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, input, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Observable } from 'rxjs';

import { Api, errorMessage } from '../core/api';
import { ShiftDetail as ShiftDetailModel, RolePlan } from '../core/models';
import { RoleLabelPipe } from '../core/role-label-pipe';

@Component({
  selector: 'app-shift-detail',
  imports: [RouterLink, DatePipe, RoleLabelPipe],
  templateUrl: './shift-detail.html',
})
export class ShiftDetail implements OnInit {
  private readonly api = inject(Api);
  private readonly router = inject(Router);

  /** Route parameter, bound by withComponentInputBinding(). */
  readonly id = input.required<string>();

  protected readonly shift = signal<ShiftDetailModel | null>(null);
  protected readonly plan = signal<RolePlan[] | null>(null);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly assignedByRole = computed(() => {
    const counts = new Map<string, number>();
    for (const assignment of this.shift()?.assignments ?? []) {
      counts.set(assignment.role, (counts.get(assignment.role) ?? 0) + 1);
    }
    return counts;
  });

  protected readonly proposedCount = computed(() =>
    (this.plan() ?? []).reduce((total, role) => total + role.candidates.length, 0),
  );

  ngOnInit(): void {
    this.load();
  }

  protected findStaff(): void {
    this.run(this.api.plan(this.shiftId), (plan) => this.plan.set(plan));
  }

  protected confirmAssignments(): void {
    this.run(this.api.assign(this.shiftId), (shift) => {
      this.shift.set(shift);
      this.plan.set(null);
    });
  }

  protected removeAssignment(assignmentId: number): void {
    this.run(this.api.removeAssignment(assignmentId), () => this.load());
  }

  protected deleteShift(): void {
    if (!confirm('Delete this shift and its assignments?')) return;
    this.run(this.api.deleteShift(this.shiftId), () => this.router.navigate(['/shifts']));
  }

  private get shiftId(): number {
    return Number(this.id());
  }

  private load(): void {
    this.plan.set(null);
    this.run(this.api.shift(this.shiftId), (shift) => this.shift.set(shift));
  }

  private run<T>(request: Observable<T>, onSuccess: (value: T) => void): void {
    this.busy.set(true);
    this.error.set(null);
    request.subscribe({
      next: (value) => {
        onSuccess(value);
        this.busy.set(false);
      },
      error: (err) => {
        this.error.set(errorMessage(err));
        this.busy.set(false);
      },
    });
  }
}
