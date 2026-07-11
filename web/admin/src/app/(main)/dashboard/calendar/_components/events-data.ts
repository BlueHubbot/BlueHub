import { setDate, setHours, setMinutes, startOfMonth } from "date-fns";

const monthStart = startOfMonth(new Date());
const currentYear = new Date().getFullYear();
const d = (day: number) => setDate(monthStart, day);
const dt = (day: number, hour: number, min = 0) => setMinutes(setHours(setDate(monthStart, day), hour), min);

export const demoEvents = [
  { title: "برنامه‌ریزی ماهانه", start: dt(1, 9, 30), end: dt(1, 10, 30) },
  { title: "بررسی طراحی", start: dt(3, 11), end: dt(3, 12) },
  { title: "جلسه با مشتری", start: dt(4, 15), end: dt(4, 15, 45) },
  { title: "کارگاه محصول", start: d(7), end: d(9), allDay: true },
  { groupId: "standup", title: "جلسه ایستاده تیمی", start: dt(9, 10) },
  { title: "هماهنگی مالی", start: dt(10, 14, 30), end: dt(10, 15) },
  { title: "زمان تمرکز نهایی", start: dt(12, 9), end: dt(12, 12), display: "background" },
  { title: "برنامه‌ریزی اسپرینت", start: dt(15, 9, 30), end: dt(15, 11) },
  { groupId: "standup", title: "جلسه ایستاده تیمی", start: dt(16, 10) },
  { title: "تحویل تسک‌های فنی", start: dt(18, 16), end: dt(18, 16, 45) },
  { title: "موعد گزارش سه‌ماهه", start: d(24), allDay: true },
  { title: "روز بازنشانی سیستم", start: d(28), allDay: true },
  { title: "تولد سرمد افضلی", start: new Date(currentYear, 8, 6), allDay: true },
];