import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { ShiftForm } from './shift-form';

describe('ShiftForm', () => {
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ShiftForm],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });

  function create() {
    const fixture = TestBed.createComponent(ShiftForm);
    fixture.detectChanges();
    http.expectOne('/api/cities/').flush([{ id: 7, name: 'Bergamo', latitude: 45.7, longitude: 9.7 }]);
    http.expectOne('/api/meta/').flush({ ai_intake_enabled: true });
    return fixture;
  }

  it('fills the form from an AI draft and reports what is missing', async () => {
    const fixture = create();
    const component = fixture.componentInstance as any;

    component.requestText.setValue('Turno di notte a Bergamo, 6 OSS e 2 fisioterapisti');
    component.fillWithAi();
    http.expectOne('/api/shifts/draft-from-text/').flush({
      title: 'Turno di notte',
      date: null,
      city: 7,
      patients: 120,
      notes: '',
      requirements: [
        { role: 'CARE_ASSISTANT', quantity: 6 },
        { role: 'PHYSIOTHERAPIST', quantity: 2 },
      ],
    });
    await fixture.whenStable();

    expect(component.form.controls.city.value).toBe(7);
    expect(component.requirements.getRawValue()).toEqual([
      { role: 'CARE_ASSISTANT', quantity: 6 },
      { role: 'PHYSIOTHERAPIST', quantity: 2 },
    ]);
    expect(component.draftNotice()).toContain('date');
    expect(component.form.valid).toBe(false); // the date still has to be entered
  });

  it('does not submit an incomplete form', () => {
    const fixture = create();

    (fixture.componentInstance as any).save();

    http.expectNone('/api/shifts/');
  });

  afterEach(() => http.verify());
});
