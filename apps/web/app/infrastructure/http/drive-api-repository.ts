import { GoogleAuthError } from '~/domain/errors/google-auth-error'
import type { DriveAboutUser, DriveRepository } from '~/application/ports/drive-repository'

const DRIVE_API_BASE = 'https://www.googleapis.com/drive/v3'

interface DriveAboutDto {
  user: {
    emailAddress: string
  }
}

export class DriveApiRepository implements DriveRepository {
  async getCurrentUser(accessToken: string): Promise<DriveAboutUser> {
    try {
      const dto = await $fetch<DriveAboutDto>(`${DRIVE_API_BASE}/about`, {
        query: { fields: 'user' },
        headers: { Authorization: `Bearer ${accessToken}` }
      })
      return { email: dto.user.emailAddress }
    } catch {
      throw new GoogleAuthError('driveDenied')
    }
  }
}
