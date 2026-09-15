const LOCAL_STORAGE_KEY = "siteSettings";

const translations = {
  en: {
    home: "Home",
    aboutMe: "Journey",
    contact: "Contact",
    heroEyebrow: "Personal website",
    heroTitle: "Engineering ideas into motion.",
    heroLead:
      "I am Jargal Boldbaatar, a mechatronics student building at the intersection of automation, robotics, and curiosity.",
    heroDetail:
      "This space is where I collect the things I am learning, the values that shape me, and the direction I want my work to go next.",
    exploreJourney: "Explore my journey",
    sendEmail: "Send email",
    statUniversity: "Engineering student in Mongolia",
    statFocusValue: "3 Focuses",
    statFocusLabel: "Automation, robotics, entrepreneurship",
    statBuildValue: "Learning by building",
    statBuildLabel: "Web, systems thinking, and real-world problem solving",
    noteOriginLabel: "Origin",
    noteOriginValue: "Khentii to Ulaanbaatar",
    noteMissionLabel: "Mission",
    noteMissionValue: "Build useful things and keep growing",
    focusEyebrow: "Current direction",
    focusTitle: "The work I want to grow into",
    featureAutomationTitle: "Automation",
    featureAutomationBody:
      "I am drawn to systems that reduce friction, improve reliability, and turn repetitive work into something smarter.",
    featureRoboticsTitle: "Robotics",
    featureRoboticsBody:
      "Robotics excites me because it combines hardware, software, and engineering design into one living problem.",
    featureEntrepreneurshipTitle: "Entrepreneurship",
    featureEntrepreneurshipBody:
      "I want to build ideas that matter in the real world, not just in theory, and learn how to turn them into value.",
    storyEyebrow: "Where I come from",
    storyTitle: "A countryside childhood shaped how I think.",
    storyBodyOne:
      "I grew up in a nomadic family and spent much of my childhood close to nature. That background taught me patience, adaptability, and respect for practical work.",
    storyBodyTwo:
      "Later, school in Khentii and Baganuur expanded my world, and university gave that curiosity a technical direction.",
    readFullStory: "Read the full story",
    timelineEyebrow: "Milestones",
    timelineTitle: "A short timeline of the path so far",
    timelineOneTitle: "Born and raised close to nature",
    timelineOneBody:
      "My early years were shaped by the countryside, family, and the rhythm of a nomadic life.",
    timelineTwoTitle: "A bigger world in Baganuur",
    timelineTwoBody:
      "Moving for school gave me new environments, new discipline, and a broader view of what I could become.",
    timelineThreeTitle: "Engineering at GMIT",
    timelineThreeBody:
      "University turned my interest in how things work into a serious commitment to engineering and innovation.",
    contactEyebrow: "Let's connect",
    contactTitle: "I'm building this chapter in public.",
    contactBody:
      "If you want to talk about engineering, projects, learning, or future collaboration, I would be happy to hear from you.",
    journeyEyebrow: "Personal journey",
    journeyTitle: "From the countryside to engineering.",
    journeyLead:
      "My story begins in Khentii, moves through Baganuur, and continues today at GMIT University.",
    journeyStepOneTitle: "Childhood in the countryside",
    journeyStepOneBody:
      "I was born on June 13, 2005. I grew up surrounded by open land, animals, and the pace of rural life, especially during school holidays.",
    journeyStepTwoTitle: "First steps in education",
    journeyStepTwoBody:
      "My educational journey began at Kherlen 4th Kindergarten, and in 2011 I continued at Kherlen 4th School in Khentii Province.",
    journeyStepThreeTitle: "Learning in Baganuur",
    journeyStepThreeBody:
      'I moved to Baganuur, a district of Ulaanbaatar, where I studied at <a href="https://www.bolovsrolts.edu.mn/#" target="_blank" rel="noopener noreferrer">Bolovsrol Complex School</a> and completed high school.',
    journeyStepFourTitle: "Engineering at GMIT",
    journeyStepFourBody:
      'I began my undergraduate studies at <a href="https://www.gmit.edu.mn/eng/" target="_blank" rel="noopener noreferrer">GMIT University</a>, focusing on engineering, automation, robotics, and innovation-driven entrepreneurship.',
    rootsEyebrow: "Roots",
    rootsTitle: "The places that shaped me still travel with me.",
    rootsBodyOne:
      "These photos represent more than memories. They reflect school life in Khentii and Baganuur, time in the countryside, and the background that continues to shape my perspective.",
    rootsBodyTwo:
      "I carry that sense of place into how I learn, how I work, and how I imagine the future.",
    galleryEyebrow: "Photo journal",
    galleryTitle: "Moments from school, nature, and home",
    valuesEyebrow: "What stays with me",
    valuesTitle: "The qualities I want my work to reflect",
    valueOneTitle: "Curiosity",
    valueOneBody: "I like understanding why things work, not only how to use them.",
    valueTwoTitle: "Consistency",
    valueTwoBody: "Progress matters most when it is built through steady effort over time.",
    valueThreeTitle: "Practical ambition",
    valueThreeBody:
      "I want to aim high while staying grounded in useful, real-world outcomes.",
    footerText: "Jargal Boldbaatar. Built with curiosity and consistency."
  },
  mn: {
    home: "Нүүр",
    aboutMe: "Замнал",
    contact: "Холбогдох",
    heroEyebrow: "Хувийн вэбсайт",
    heroTitle: "Инженерийн санааг хөдөлгөөнд оруулна.",
    heroLead:
      "Би автоматжуулалт, робот техник, сониуч зангийн огтлолцолд хөгжиж буй мехатроникийн оюутан Жаргал Болдбаатар.",
    heroDetail:
      "Энд би сурч буй зүйлс, намайг тодорхойлдог үнэт зүйлс, цаашдын чиглэлээ нэгтгэн харуулж байна.",
    exploreJourney: "Замналаа үзэх",
    sendEmail: "Имэйл илгээх",
    statUniversity: "Монгол дахь инженерийн оюутан",
    statFocusValue: "3 Чиглэл",
    statFocusLabel: "Автоматжуулалт, робот техник, энтрепренершип",
    statBuildValue: "Хийж суралцах",
    statBuildLabel: "Вэб, системийн сэтгэлгээ, бодит асуудал шийдэх чадвар",
    noteOriginLabel: "Гараа",
    noteOriginValue: "Хэнтийгээс Улаанбаатар хүртэл",
    noteMissionLabel: "Зорилго",
    noteMissionValue: "Хэрэгтэй зүйл бүтээж, тасралтгүй өсөх",
    focusEyebrow: "Одоогийн чиглэл",
    focusTitle: "Цаашид өсгөж хөгжүүлэхийг хүсэж буй ажил",
    featureAutomationTitle: "Автоматжуулалт",
    featureAutomationBody:
      "Давтагддаг ажлыг илүү ухаалаг, найдвартай, үр ашигтай болгодог системүүд намайг татдаг.",
    featureRoboticsTitle: "Робот техник",
    featureRoboticsBody:
      "Робот техник нь техник хангамж, програм хангамж, инженерчлэлийн дизайныг нэг дор авчирдгаараа надад сонирхолтой.",
    featureEntrepreneurshipTitle: "Энтрепренершип",
    featureEntrepreneurshipBody:
      "Би зөвхөн онолд биш, бодит амьдралд үнэ цэн бүтээх санаанууд дээр ажиллахыг хүсдэг.",
    storyEyebrow: "Миний эхлэл",
    storyTitle: "Хөдөөгийн хүүхэд нас миний сэтгэлгээг бүтээсэн.",
    storyBodyOne:
      "Би нүүдэлчин гэр бүлд өссөн бөгөөд хүүхэд насныхаа ихэнх хугацааг байгальд ойр өнгөрүүлсэн. Энэ нь тэвчээр, дасан зохицох чадвар, бодит хөдөлмөрийг хүндэтгэх чанарыг өгсөн.",
    storyBodyTwo:
      "Дараа нь Хэнтий, Багануур дахь сургуулийн амьдрал миний ертөнцийг тэлж, их сургууль тэр сониуч байдлыг техникийн чиглэл болгосон.",
    readFullStory: "Дэлгэрэнгүй унших",
    timelineEyebrow: "Товч замнал",
    timelineTitle: "Одоог хүртэлх замналын гол мөчүүд",
    timelineOneTitle: "Байгальд ойр өссөн нь",
    timelineOneBody:
      "Миний эхний жилүүдийг хөдөө нутаг, гэр бүл, нүүдэлчин амьдралын хэмнэл тодорхойлсон.",
    timelineTwoTitle: "Багануур дахь шинэ ертөнц",
    timelineTwoBody:
      "Сургуульдаа шилжин суралцсан нь шинэ орчин, илүү хариуцлага, өөрийгөө илүү томоор харах боломжийг өгсөн.",
    timelineThreeTitle: "GMIT дахь инженерчлэл",
    timelineThreeBody:
      "Их сургууль миний юмсыг хэрхэн ажилладгийг сонирхдог занг инженерчлэл, инновац руу бодитоор чиглүүлсэн.",
    contactEyebrow: "Холбоо барья",
    contactTitle: "Би энэ үе шатаа нээлттэйгээр бүтээж байна.",
    contactBody:
      "Инженерчлэл, төсөл, суралцах үйл явц эсвэл ирээдүйн хамтын ажиллагааны талаар ярилцахыг хүсвэл надтай холбоо бариарай.",
    journeyEyebrow: "Хувийн замнал",
    journeyTitle: "Хөдөө нутгаас инженерчлэл рүү.",
    journeyLead:
      "Миний түүх Хэнтийгээс эхэлж, Багануураар дамжин, өнөөдөр GMIT их сургуульд үргэлжилж байна.",
    journeyStepOneTitle: "Хөдөөгийн хүүхэд нас",
    journeyStepOneBody:
      "Би 2005 оны 6-р сарын 13-нд төрсөн. Амралтын үеэрээ ялангуяа өргөн тал нутаг, мал сүрэг, хөдөөгийн амьдралын хэмнэл дунд өссөн.",
    journeyStepTwoTitle: "Боловсролын эхлэл",
    journeyStepTwoBody:
      "Миний боловсролын замнал Хэрлэн 4-р цэцэрлэгээс эхэлж, 2011 онд Хэнтий аймгийн Хэрлэн 4-р сургуульд үргэлжилсэн.",
    journeyStepThreeTitle: "Багануур дахь суралцах он жилүүд",
    journeyStepThreeBody:
      'Би Улаанбаатар хотын Багануур дүүрэгт нүүж, <a href="https://www.bolovsrolts.edu.mn/#" target="_blank" rel="noopener noreferrer">Боловсрол Цогцолбор Сургууль</a>-д суралцан ахлах сургуулиа төгссөн.',
    journeyStepFourTitle: "GMIT дахь инженерийн зам",
    journeyStepFourBody:
      'Би <a href="https://www.gmit.edu.mn/eng/" target="_blank" rel="noopener noreferrer">GMIT University</a>-д инженерийн чиглэлээр бакалаврын сургалтаа эхлүүлж, автоматжуулалт, робот техник, инновацид суурилсан энтрепренершипт төвлөрч байна.',
    rootsEyebrow: "Өссөн орчин",
    rootsTitle: "Намайг бүтээсэн газрууд надтай хамт явсаар байна.",
    rootsBodyOne:
      "Эдгээр зургууд нь зүгээр нэг дурсамж биш. Хэнтий, Багануур дахь сургуулийн амьдрал, хөдөө нутаг, мөн миний өнцгийг тодорхойлсон орчныг илэрхийлдэг.",
    rootsBodyTwo:
      "Би тэр мэдрэмжээ суралцах арга барил, ажиллах хандлага, ирээдүйгээ төсөөлөх үзэлдээ авч явдаг.",
    galleryEyebrow: "Зургийн тэмдэглэл",
    galleryTitle: "Сургууль, байгаль, гэр орны мөчүүд",
    valuesEyebrow: "Надад үлдсэн зүйлс",
    valuesTitle: "Миний ажилд тусгагдаасай гэж хүсдэг чанарууд",
    valueOneTitle: "Сониуч зан",
    valueOneBody: "Би зүйлийг зөвхөн ашиглахаас гадна яагаад ажилладгийг ойлгох дуртай.",
    valueTwoTitle: "Тууштай байдал",
    valueTwoBody: "Жинхэнэ ахиц нь тогтвортой, өдөр тутмын хүчин чармайлтаас бий болдог.",
    valueThreeTitle: "Бодит амбиц",
    valueThreeBody: "Би өндөр зорилготой байж, бодит амьдрал дахь хэрэгцээнд түшиглэн ажиллахыг хүсдэг.",
    footerText: "Жаргал Болдбаатар. Сониуч зан ба тууштай байдлаар бүтээв."
  }
};

function applyTranslations(language) {
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    const key = node.getAttribute("data-i18n");
    const value = translations[language]?.[key];

    if (value) {
      node.textContent = value;
    }
  });

  document.querySelectorAll("[data-i18n-html]").forEach((node) => {
    const key = node.getAttribute("data-i18n-html");
    const value = translations[language]?.[key];

    if (value) {
      node.innerHTML = value;
    }
  });
}

function setLanguage(language) {
  const current = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEY) || "{}");

  localStorage.setItem(
    LOCAL_STORAGE_KEY,
    JSON.stringify({ ...current, language })
  );

  document.documentElement.lang = language;
  applyTranslations(language);

  if (typeof window.updateLanguageToggle === "function") {
    window.updateLanguageToggle(language);
  }
}

window.switchLanguage = setLanguage;
window.applyTranslations = applyTranslations;

document.addEventListener("DOMContentLoaded", () => {
  const saved = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEY) || "{}");
  const language = saved.language || "en";
  setLanguage(language);
});
