/// calculateGradient
public calculateGradient = (highway: string, line: number[][]) => {
    let fp = line[0];
    let ep = line[line.length - 1];
    let zValue = fp[2] - ep[2];
    let length = turf.distance(
      turf.point([fp[0], fp[1]]),
      turf.point([ep[0], ep[1]]),
      { units: "meters" }
    );
    let gradient =
      zValue === 0
        ? 0
        : length === 0 || highway === "lift"
        ? Math.PI / 2
        : Math.atan2(zValue, length);
    return Math.abs(gradient);
  };

  //// calculatFeatureType by unit 
  public calculatFeatureType = (
    nf: I3DNetworkFeature,
    unitFeatures: IUnitFeature[],
    unit3DFeatures: I3DUnitFeature[]
  ) => {
    const level_id = nf.properties.level_id;
    if (unitFeatures) {
      const line = this._spatial.removeZ(
        nf as Feature<LineString>
      ) as Feature<LineString>;

      // Step 3: Identify intersecting or containing units
      const intersectingUnits = unitFeatures.filter((unit) => {
        const polygon = this._spatial.removeZ(
          unit as Feature<Polygon>
        ) as Feature<Polygon>;
        return (
          turf.booleanIntersects(line, polygon) ||
          turf.booleanWithin(line, polygon)
        );
      });

      // Step 4: Determine FeatureType based on intersections
      if (intersectingUnits.length === 0) {
        // No intersection: FeatureType = 1
        nf.properties.FeatureType = UnitFeatureTypeMap["walkway"];
      } else if (intersectingUnits.length === 1) {
        this.findStairLiftFeatureType(nf, intersectingUnits[0], unit3DFeatures);
        if (nf.properties.FeatureType !== 13) {
          // Single intersection: Use unit category to determine FeatureType
          const unitCategory =
            intersectingUnits[0].properties.category.toLowerCase();
          nf.properties.FeatureType =
            UnitFeatureTypeMap[unitCategory] || UnitFeatureTypeMap["walkway"];
        }
      } else {
        // Multiple intersections
        const zValues = nf.geometry?.coordinates.map((c) => {
          const coord = c as number[];
          return coord[2];
        }) as number[];

        if (!this._utils.areAllValuesSame(zValues)) {
          // Z-values are not the same: Check for special unit types
          let specialUnit = intersectingUnits.find((unit) =>
            ["stairs", "escalator", "elevator"].includes(
              unit.properties.category.toLowerCase()
            )
          );
          if (specialUnit) {
            const unitCategory = specialUnit.properties.category.toLowerCase();
            nf.properties.FeatureType =
              UnitFeatureTypeMap[unitCategory] || UnitFeatureTypeMap["walkway"];
          } else {
            specialUnit = intersectingUnits.find(
              (unit) => unit.properties.category === "ramp"
            );
            if (specialUnit) {
              nf.properties.FeatureType = UnitFeatureTypeMap["ramp"];
            } else {
              nf.properties.FeatureType = UnitFeatureTypeMap["walkway"];
            }
          }
        } else {
          // Z-values are the same: Find the unit covering the longest portion of the line
          const longestUnit = this._spatial.findMaxCoveragePolygon(
            line,
            intersectingUnits as Feature<Polygon>[]
          ) as IUnitFeature;
          if (longestUnit) {
            this.findStairLiftFeatureType(nf, longestUnit, unit3DFeatures);
            if (nf.properties.FeatureType !== 13) {
              const unitCategory =
                longestUnit.properties.category.toLowerCase();
              nf.properties.FeatureType =
                UnitFeatureTypeMap[unitCategory] ||
                UnitFeatureTypeMap["walkway"];
            }
          } else {
            nf.properties.FeatureType = 1;
          }
        }
      }
    }
  };

  public findStairLiftFeatureType = (
    nf: I3DNetworkFeature,
    unit: IUnitFeature,
    unit3dFeatures: I3DUnitFeature[]
  ) => {
    if (unit.properties.category === "unspecified") {
      const unit3d = unit3dFeatures.find(
        (u) => u.properties.UnitPolyID === unit.properties.UnitPolyID
      );
      if (
        (unit.properties.name as IName).en === "stairlift" ||
        (unit3d && unit3d.properties.UnitSubtype === "12-03")
      ) {
        nf.properties.FeatureType = 13;
      }
    }
  };

  public findMaxCoveragePolygon(
    line: Feature<LineString>,
    polygons: Feature<Polygon | MultiPolygon>[]
  ): Feature<Polygon | MultiPolygon> | null {
    let mostCoveredPolygon = null;
    let longestCoveredLength = 0;

    for (const polygon of polygons) {
      const longestSegment = this.findLongestSegmentInPolygon(line, polygon);

      if (longestSegment) {
        const segmentLength = turf.length(longestSegment, {
          units: "kilometers",
        });

        if (segmentLength > longestCoveredLength) {
          longestCoveredLength = segmentLength;
          mostCoveredPolygon = polygon;
        }
      }
    }
    return mostCoveredPolygon;
  }

  ///// featuretype by unit 

  export const facilityMap = new Map<number, Facility>([
    [8, { code: 8, nameEn: "Escalator", nameZh: "扶手電梯" }],
    [9, { code: 9, nameEn: "Travelator", nameZh: "自動行人道" }],
    [10, { code: 10, nameEn: "Lift", nameZh: "升降機" }],
    [11, { code: 11, nameEn: "Ramp", nameZh: "斜道" }],
    [12, { code: 12, nameEn: "Staircase", nameZh: "樓梯" }],
    [13, { code: 13, nameEn: "Stairlift", nameZh: "輪椅升降台" }],
  ]);
  export const UnitFeatureTypeMap: Record<string, number> = {
    walkway: 1,
    room: 1,
    unspecified: 1,
    footbridge: 2,
    escalator: 8,
    elevator: 10,
    ramp: 11,
    movingwalkway: 9,
    stairs: 12,
    steps: 12,
    staircase: 12,
    stairlift: 13,
    "N/A": 14,
  };



  export const facilityMap = new Map<number, Facility>([
    [8, { code: 8, nameEn: "Escalator", nameZh: "扶手電梯" }],
    [9, { code: 9, nameEn: "Travelator", nameZh: "自動行人道" }],
    [10, { code: 10, nameEn: "Lift", nameZh: "升降機" }],
    [11, { code: 11, nameEn: "Ramp", nameZh: "斜道" }],
    [12, { code: 12, nameEn: "Staircase", nameZh: "樓梯" }],
    [13, { code: 13, nameEn: "Stairlift", nameZh: "輪椅升降台" }],
  ]);


  public calculateWheelchairAccess = (
    nf: I3DNetworkFeature,
    openingFeatures: IOpeningFeature[]
  ) => {
    if (nf.properties.FeatureType === 11) {
      const level_id = nf.properties.level_id;
      const filterOpening = openingFeatures.filter(
        (of) => of.properties.level_id === level_id
      );
      if (filterOpening.length > 0) {
        let wheelchairAccess = false;
        for (let e of filterOpening) {
          const bufferArea = turf.buffer(e as Feature<LineString>, 0.1 / 1000, {
            units: "kilometers",
          }) as Feature<Polygon>;
          const intersect = turf.booleanIntersects(
            bufferArea as Feature<Polygon>,
            nf as Feature<LineString>
          );
          if (intersect) {
            nf.properties.WheelchairAccess = 1;
            wheelchairAccess = true;
            break;
          }
        }
        if (!wheelchairAccess) {
          nf.properties.WheelchairAccess = 2;
        }
      } else {
        nf.properties.WheelchairAccess = 2;
      }
    } else {
      nf.properties.WheelchairAccess = 2;
    }
  };


  public getAliceName = (
    nf: I3DNetworkFeature,
    openingFeatures: IOpeningFeature[]
  ) => {
    const level_id = nf.properties.level_id;
    const featureTypeName = facilityMap.get(
      nf.properties.FeatureType as number
    );
    const buildingEngName = nf.properties.BuildingNameEng;
    const buildinZhName = nf.properties.BuildingNameChi;
    const levelEngName = nf.properties.LevelEnglishName;
    const levelZhName = nf.properties.LevelChineseName;
    const exits = openingFeatures
      ? openingFeatures.filter((e) => e.properties.level_id === level_id)
      : [];
    if (exits.length > 0) {
      let matchExit = false;
      for (let e of exits) {
        const bufferArea = turf.buffer(e as Feature<LineString>, 0.1 / 1000, {
          units: "kilometers",
        }) as Feature<Polygon>;
        const intersect = turf.booleanIntersects(
          bufferArea as Feature<Polygon>,
          nf as Feature<LineString>
        );
        if (intersect) {
          nf.properties.AliasNameEN = featureTypeName
            ? `${buildingEngName} ${e.properties.name?.en} ${featureTypeName.nameEn}`
            : `${buildingEngName} ${e.properties.name?.en}`;
          nf.properties.AliasNameTC = featureTypeName
            ? `${buildinZhName}${e.properties.name?.zh}${featureTypeName.nameZh}`.replace(
                /\s/g,
                ""
              )
            : `${buildinZhName}${e.properties.name?.zh}`.replace(/\s/g, "");
          nf.properties.exit = {
            en: e.properties.name?.en,
            zh: e.properties.name?.zh,
          };
          nf.properties.BuildingNameEng = buildingEngName;
          nf.properties.BuildingNameChi = buildinZhName;
          matchExit = true;
          break;
        }
      }
      if (!matchExit) {
        nf.properties.AliasNameEN = featureTypeName
          ? `${buildingEngName} ${featureTypeName.nameEn}`
          : `${buildingEngName} ${levelEngName}`;
        nf.properties.AliasNameTC = featureTypeName
          ? `${buildinZhName}${featureTypeName.nameZh}`
              .trim()
              .replace(/\s/g, "")
          : `${buildinZhName}${levelZhName}`.trim().replace(/\s/g, "");
        nf.properties.exit = null;
        nf.properties.BuildingNameEng = buildingEngName;
        nf.properties.BuildingNameChi = buildinZhName;
      }
    } else {
      nf.properties.AliasNameEN = featureTypeName
        ? `${buildingEngName} ${featureTypeName.nameEn}`
        : `${buildingEngName} ${levelEngName}`;
      nf.properties.AliasNameTC = featureTypeName
        ? `${buildinZhName}${featureTypeName.nameZh}`.trim().replace(/\s/g, "")
        : `${buildinZhName}${levelZhName}`.trim().replace(/\s/g, "");
      nf.properties.exit = null;
    }
  };