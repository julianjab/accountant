export interface DriveAboutUser {
  email: string
}

export interface DriveRepository {
  getCurrentUser: (accessToken: string) => Promise<DriveAboutUser>
}
