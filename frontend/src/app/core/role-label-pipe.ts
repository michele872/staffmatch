import { Pipe, PipeTransform } from '@angular/core';

import { ROLE_LABELS, Role } from './models';

@Pipe({ name: 'roleLabel' })
export class RoleLabelPipe implements PipeTransform {
  transform(role: Role): string {
    return ROLE_LABELS[role] ?? role;
  }
}
