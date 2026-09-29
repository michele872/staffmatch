import { Component, OnInit, inject, signal } from '@angular/core';
import { FormArray, FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { Api, errorMessage } from '../core/api';
import { City, ShiftDraft, NewShift, ROLES, Role } from '../core/models';
import { RoleLabelPipe } from '../core/role-label-pipe';

type RequirementForm = FormGroup<{
  role: FormControl<Role>;
  quantity: FormControl<number>;
}>;

@Component({
  selector: 'app-shift-form',
  imports: [ReactiveFormsModule, RouterLink, RoleLabelPipe],
  templateUrl: './shift-form.html',
})
export class ShiftForm implements OnInit {
  private readonly api = inject(Api);
  private readonly router = inject(Router);

  protected readonly roles = ROLES;
  protected readonly cities = signal<City[]>([]);
  protected readonly aiEnabled = signal(false);
  protected readonly saving = signal(false);
  protected readonly drafting = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly draftNotice = signal<string | null>(null);

  protected readonly requestText = new FormControl('', { nonNullable: true });

  protected readonly form = new FormGroup({
    title: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    date: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    city: new FormControl<number | null>(null, { validators: [Validators.required] }),
    patients: new FormControl<number | null>(null, {
      validators: [Validators.required, Validators.min(1)],
    }),
    notes: new FormControl('', { nonNullable: true }),
    requirements: new FormArray<RequirementForm>([this.requirement('CARE_ASSISTANT', 1)]),
  });

  ngOnInit(): void {
    this.api.cities().subscribe((cities) => this.cities.set(cities));
    this.api.meta().subscribe((meta) => this.aiEnabled.set(meta.ai_intake_enabled));
  }

  protected get requirements(): FormArray<RequirementForm> {
    return this.form.controls.requirements;
  }

  protected addRequirement(): void {
    const used = new Set(this.requirements.getRawValue().map((r) => r.role));
    const next = ROLES.find((role) => !used.has(role));
    if (next) this.requirements.push(this.requirement(next, 1));
  }

  protected removeRequirement(index: number): void {
    this.requirements.removeAt(index);
  }

  /** Ask the backend (and Claude) to turn the free-text request into a draft. */
  protected fillWithAi(): void {
    const text = this.requestText.value.trim();
    if (!text) return;
    this.drafting.set(true);
    this.error.set(null);
    this.api.draftFromText(text).subscribe({
      next: (draft) => {
        this.applyDraft(draft);
        this.drafting.set(false);
      },
      error: (err) => {
        this.error.set(errorMessage(err));
        this.drafting.set(false);
      },
    });
  }

  protected save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    this.api.createShift(this.form.getRawValue() as NewShift).subscribe({
      next: (shift) => this.router.navigate(['/shifts', shift.id]),
      error: (err) => {
        this.error.set(errorMessage(err));
        this.saving.set(false);
      },
    });
  }

  protected invalid(name: 'title' | 'date' | 'city' | 'patients'): boolean {
    const control = this.form.controls[name];
    return control.invalid && control.touched;
  }

  private applyDraft(draft: ShiftDraft): void {
    const missing: string[] = [];
    this.form.patchValue({ title: draft.title, notes: draft.notes });
    if (draft.date) this.form.patchValue({ date: draft.date });
    else missing.push('date');
    if (draft.city) this.form.patchValue({ city: draft.city });
    else missing.push('city');
    if (draft.patients) this.form.patchValue({ patients: draft.patients });
    else missing.push('patients');

    if (draft.requirements.length) {
      this.requirements.clear();
      for (const item of draft.requirements) {
        this.requirements.push(this.requirement(item.role, item.quantity));
      }
    } else {
      missing.push('staff roles');
    }

    this.draftNotice.set(
      missing.length
        ? `Draft filled in. Not found in the request: ${missing.join(', ')}. Please complete and review before saving.`
        : 'Draft filled in. Please review it before saving.',
    );
  }

  private requirement(role: Role, quantity: number): RequirementForm {
    return new FormGroup({
      role: new FormControl<Role>(role, { nonNullable: true }),
      quantity: new FormControl(quantity, {
        nonNullable: true,
        validators: [Validators.required, Validators.min(1)],
      }),
    });
  }
}
