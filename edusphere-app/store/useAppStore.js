import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import AsyncStorage from "@react-native-async-storage/async-storage";

export const useAppStore = create(
  persist(
    (set) => ({
      academicYear: null,
      academicYears: [],
      institution: null,
      theme: "light",

      setAcademicYear: (academicYear) => set({ academicYear }),
      setAcademicYears: (academicYears) => set({ academicYears }),
      setInstitution: (institution) => set({ institution }),
      setTheme: (theme) => set({ theme }),

      initFromLogin: (user) =>
        set({
          academicYear: user.current_academic_year || null,
          academicYears: user.academic_years || [],
          institution: {
            id: user.institution_id,
            name: user.institution_name,
            code: user.institution_code,
            skid: user.skid,
          },
        }),

      reset: () =>
        set({
          academicYear: null,
          academicYears: [],
          institution: null,
          theme: "light",
        }),
    }),
    {
      name: "edusphere-app",
      storage: createJSONStorage(() => AsyncStorage),
    }
  )
);
